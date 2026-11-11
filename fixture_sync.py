import csv
import io
import os
import json
import requests

from datetime import datetime, date

URL = "https://www.football-data.co.uk/fixtures.csv"
CACHE_FILE = "data/fixtures_source.csv"
STAMP_FILE = "data/fixtures_source.json"
OUTPUT_FILE = "upcoming.csv"

ALLOWED = {"E1", "E2", "E3", "EC"}
CACHE_DAYS = 4


def normalise_headers(row):
    return {
        str(k).strip().lower().replace("_", "").replace(" ", ""):
        (v or "").strip()
        for k, v in row.items()
        if k is not None
    }


def get_value(row, *names):
    for name in names:
        value = row.get(name.lower().replace("_", "").replace(" ", ""))
        if value:
            return value.strip()
    return ""


def parse_match_date(value):
    for fmt in ("%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except (ValueError, AttributeError):
            pass
    return None


def get_feed():
    os.makedirs("data", exist_ok=True)

    if os.path.exists(CACHE_FILE) and os.path.exists(STAMP_FILE):
        try:
            with open(STAMP_FILE) as f:
                stamp = json.load(f)

            age = datetime.now().timestamp() - stamp["time"]

            if age < CACHE_DAYS * 86400:
                print("Using cached fixture feed.")
                with open(CACHE_FILE, encoding="utf-8-sig") as f:
                    return f.read()
        except Exception:
            pass

    print("Downloading fixture feed...")
    response = requests.get(URL, timeout=30)
    response.raise_for_status()

    content = response.content.decode("utf-8-sig")

    if not content.strip():
        raise ValueError("The fixture feed is empty.")

    with open(CACHE_FILE, "w", encoding="utf-8", newline="") as f:
        f.write(content)

    with open(STAMP_FILE, "w") as f:
        json.dump({"time": datetime.now().timestamp()}, f)

    return content


def sync_fixtures():
    try:
        content = get_feed()
        reader = csv.DictReader(io.StringIO(content))

        if not reader.fieldnames:
            raise ValueError("Fixture feed has no CSV headers.")

        fixtures = []
        today = date.today()

        for original in reader:
            row = normalise_headers(original)

            division = get_value(row, "div", "division").upper()
            if division not in ALLOWED:
                continue

            raw_date = get_value(row, "date", "matchdate")
            match_date = parse_match_date(raw_date)

            home = get_value(row, "hometeam", "home_team")
            away = get_value(row, "awayteam", "away_team")

            if not match_date or match_date < today:
                continue

            if not home or not away:
                continue

            fixtures.append({
                "Div": division,
                "Date": match_date.strftime("%d/%m/%Y"),
                "HomeTeam": home,
                "AwayTeam": away
            })

        if not fixtures:
            print("No matching future fixtures in the downloaded feed.")
            print("Keeping your existing upcoming.csv unchanged.")
            return

        fixtures.sort(key=lambda x: (x["Date"], x["Div"]))

        with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
            fields = ["Div", "Date", "HomeTeam", "AwayTeam"]
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(fixtures)

        print("Fixture sync successful.")
        print("Future fixtures found:", len(fixtures))
        print("Updated:", OUTPUT_FILE)

    except Exception as error:
        print("Fixture sync could not complete:", error)
        print("Your existing upcoming.csv has not been changed.")
