#!/data/data/com.termux/files/usr/bin/bash

set -e

echo "Installing England Predictor V1..."

pkg install python -y
pip install --upgrade requests

mkdir -p data
mkdir -p backups

cat > predictor.py <<'PY'
import csv
import io
import json
import math
import os
import requests

from datetime import datetime, date, timedelta

BASE = "https://www.football-data.co.uk/mmz4281/2627"

LEAGUES = {
    "E1": "Championship",
    "E2": "League One",
    "E3": "League Two",
    "EC": "National League"
}

DATA_DIR = "data"
FIXTURES_FILE = "upcoming.csv"
OUTPUT_FILE = "predictions.csv"
CACHE_DAYS = 7

os.makedirs(DATA_DIR, exist_ok=True)

def parse_date(value):
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except (ValueError, AttributeError):
            pass
    return None


def download_data(code):
    path = f"{DATA_DIR}/{code}.csv"
    stamp = path + ".json"

    if os.path.exists(path) and os.path.exists(stamp):
        try:
            with open(stamp) as f:
                saved = json.load(f)

            age = datetime.now().timestamp() - saved["time"]

            if age < CACHE_DAYS * 86400:
                print(f"Using cached {LEAGUES[code]} data")
                return path
        except Exception:
            pass

    url = f"{BASE}/{code}.csv"
    print(f"Downloading {LEAGUES[code]}...")

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    with open(path, "wb") as f:
        f.write(response.content)

    with open(stamp, "w") as f:
        json.dump({"time": datetime.now().timestamp()}, f)

    return path


def load_results():
    all_results = {code: [] for code in LEAGUES}

    for code in LEAGUES:
        path = download_data(code)

        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                match_date = parse_date(row.get("Date"))

                try:
                    hg = int(row["FTHG"])
                    ag = int(row["FTAG"])
                    home = row["HomeTeam"].strip()
                    away = row["AwayTeam"].strip()
                except (ValueError, TypeError, KeyError, AttributeError):
                    continue

                if not home or not away or not match_date:
                    continue

                all_results[code].append({
                    "date": match_date,
                    "home": home,
                    "away": away,
                    "hg": hg,
                    "ag": ag
                })

        all_results[code].sort(key=lambda x: x["date"])

    return all_results


def build_stats(matches):
    teams = {}

    def create(name):
        if name not in teams:
            teams[name] = {
                "all": [],
                "home": [],
                "away": [],
                "points": 0,
                "played": 0,
                "gf": 0,
                "ga": 0
            }
        return teams[name]

    for m in matches:
        h = create(m["home"])
        a = create(m["away"])

        h["all"].append((m["date"], m["hg"], m["ag"]))
        h["home"].append((m["date"], m["hg"], m["ag"]))

        a["all"].append((m["date"], m["ag"], m["hg"]))
        a["away"].append((m["date"], m["ag"], m["hg"]))

        h["played"] += 1
        a["played"] += 1

        h["gf"] += m["hg"]
        h["ga"] += m["ag"]
        a["gf"] += m["ag"]
        a["ga"] += m["hg"]

        if m["hg"] > m["ag"]:
            h["points"] += 3
        elif m["hg"] < m["ag"]:
            a["points"] += 3
        else:
            h["points"] += 1
            a["points"] += 1

    for team in teams.values():
        team["all"].sort(key=lambda x: x[0])
        team["home"].sort(key=lambda x: x[0])
        team["away"].sort(key=lambda x: x[0])

    return teams


def average(values, fallback):
    return sum(values) / len(values) if values else fallback


def form_points(team):
    recent = team["all"][-10:]
    points = 0

    for _, gf, ga in recent:
        if gf > ga:
            points += 3
        elif gf == ga:
            points += 1

    return points


def poisson(lam, goals):
    return math.exp(-lam) * (lam ** goals) / math.factorial(goals)


def calculate_probabilities(home_xg, away_xg):
    limit = 11

    home_probs = [poisson(home_xg, i) for i in range(limit)]
    away_probs = [poisson(away_xg, i) for i in range(limit)]

    scores = []

    for h in range(limit):
        for a in range(limit):
            scores.append((h, a, home_probs[h] * away_probs[a]))

    total = sum(p for _, _, p in scores)
    scores = [(h, a, p / total) for h, a, p in scores]

    p_home = sum(p for h, a, p in scores if h > a)
    p_draw = sum(p for h, a, p in scores if h == a)
    p_away = sum(p for h, a, p in scores if h < a)

    p_over15 = sum(p for h, a, p in scores if h + a >= 2)
    p_over25 = sum(p for h, a, p in scores if h + a >= 3)
    p_under35 = sum(p for h, a, p in scores if h + a <= 3)

    p_btts = sum(p for h, a, p in scores if h >= 1 and a >= 1)

    markets = {
        "Home win": p_home,
        "Draw": p_draw,
        "Away win": p_away,
        "1X": p_home + p_draw,
        "X2": p_away + p_draw,
        "12": p_home + p_away,
        "Over 1.5": p_over15,
        "Over 2.5": p_over25,
        "Under 3.5": p_under35,
        "BTTS Yes": p_btts,
        "BTTS No": 1 - p_btts
    }

    return markets


def expected_goals(home, away, league_home, league_away):
    home_form = home["home"][-10:]
    away_form = away["away"][-10:]

    home_attack = average(
        [x[1] for x in home_form], league_home
    )
    away_defence = average(
        [x[2] for x in away_form], league_home
    )

    away_attack = average(
        [x[1] for x in away_form], league_away
    )
    home_defence = average(
        [x[2] for x in home_form], league_away
    )

    hxg = (home_attack + away_defence + league_home) / 3
    axg = (away_attack + home_defence + league_away) / 3

    return max(0.15, min(hxg, 4.5)), max(0.15, min(axg, 4.5))


def read_fixtures():
    if not os.path.exists(FIXTURES_FILE):
        with open(FIXTURES_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Div", "Date", "HomeTeam", "AwayTeam"])
        return []

    fixtures = []

    with open(FIXTURES_FILE, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            code = (row.get("Div") or "").strip()
            match_date = parse_date(row.get("Date"))
            home = (row.get("HomeTeam") or "").strip()
            away = (row.get("AwayTeam") or "").strip()

            if (
                code in LEAGUES
                and match_date
                and match_date >= date.today()
                and home and away
            ):
                fixtures.append({
                    "div": code,
                    "date": match_date,
                    "home": home,
                    "away": away
                })

    return fixtures


def main():
    print("\nENGLAND MATCH PREDICTOR V1")
    print("==========================\n")

    results = load_results()
    fixtures = read_fixtures()

    if not fixtures:
        print("\nNo upcoming fixtures found.")
        print("Add fixtures to upcoming.csv")
        print("Format: Div,Date,HomeTeam,AwayTeam")
        print("Date format: DD/MM/YYYY")
        print("Division codes: E1, E2, E3, EC")
        print("\nHistorical data has been saved in the data folder.")
        return

    output = []

    for fixture in fixtures:
        code = fixture["div"]
        matches = results[code]
        stats = build_stats(matches)

        home_name = fixture["home"]
        away_name = fixture["away"]

        if home_name not in stats or away_name not in stats:
            print(
                "Skipping unknown team:",
                home_name, "vs", away_name
            )
            continue

        home = stats[home_name]
        away = stats[away_name]

        relevant = [
            m for m in matches
            if m["date"] < fixture["date"]
        ]

        if len(home["all"]) < 3 or len(away["all"]) < 3:
            continue

        home_matches = [
            m for m in relevant
            if m["home"] == home_name
        ]
        away_matches = [
            m for m in relevant
            if m["away"] == away_name
        ]

        league_home = average(
            [m["hg"] for m in relevant], 1.4
        )
        league_away = average(
            [m["ag"] for m in relevant], 1.1
        )

        hxg, axg = expected_goals(home, away, league_home, league_away)

        markets = calculate_probabilities(hxg, axg)

        best_market = max(markets, key=markets.get)
        best_probability = markets[best_market]

        output.append({
            "date": fixture["date"].isoformat(),
            "league": LEAGUES[code],
            "home": home_name,
            "away": away_name,
            "home_form": form_points(home),
            "away_form": form_points(away),
            "home_xg": round(hxg, 2),
            "away_xg": round(axg, 2),
            "best_market": best_market,
            "best_probability": round(best_probability * 100, 1),
            "markets": markets
        })

    output.sort(key=lambda x: x["best_probability"], reverse=True)
    top = output[:10]

    if not top:
        print("No matches could be analysed.")
        return

    with open(OUTPUT_FILE, "w", newline="") as f:
        fields = [
            "date", "league", "home", "away",
            "home_form", "away_form",
            "home_xg", "away_xg",
            "best_market", "best_probability"
        ]

        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        for item in top:
            writer.writerow({
                k: item[k] for k in fields
            })

    print("\nTOP 10 MATCH SELECTIONS")
    print("======================")

    for i, item in enumerate(top, 1):
        print(f"\n{i}. {item['home']} vs {item['away']}")
        print(f"   League: {item['league']}")
        print(f"   Date: {item['date']}")
        print(f"   Form points: {item['home_form']} - {item['away_form']}")
        print(f"   Expected goals: {item['home_xg']} - {item['away_xg']}")
        print(
            f"   Best market: {item['best_market']} "
            f"({item['best_probability']}%)"
        )

        for market, probability in sorted(
            item["markets"].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            print(f"   {market}: {probability * 100:.1f}%")

    print("\nSaved results to predictions.csv")
    print("Remember: these are statistical estimates, not guarantees.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("\nERROR:", error)
PY

cat > upcoming.csv <<'CSV'
Div,Date,HomeTeam,AwayTeam
CSV

echo ""
echo "Installation complete!"
echo "Historical data will be downloaded once and cached for 7 days."
echo "Upcoming fixtures go in upcoming.csv."
echo ""
echo "Run with: python predictor.py"
