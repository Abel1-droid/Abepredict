
import requests
import csv
import io
from datetime import datetime, date

BASE = "https://www.football-data.co.uk/mmz4281/2627"

leagues = {
    "E1": "Championship",
    "E2": "League One",
    "E3": "League Two",
    "EC": "National League"
}

today = date.today()

for code, name in leagues.items():
    url = f"{BASE}/{code}.csv"

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()

        rows = csv.DictReader(io.StringIO(response.content.decode("utf-8-sig")))

        upcoming = []

        for row in rows:
            if not row.get("Date"):
                continue

            try:
                match_date = datetime.strptime(
                    row["Date"], "%d/%m/%Y"
                ).date()
            except ValueError:
                continue

            if match_date >= today and not row.get("FTHG", "").strip():
                upcoming.append(row)

        print(f"\n{name}: {len(upcoming)} upcoming fixtures")

        for match in upcoming[:5]:
            print(
                match.get("Date"),
                match.get("HomeTeam"),
                "vs",
                match.get("AwayTeam")
            )

    except Exception as error:
        print(name, "ERROR:", error)
