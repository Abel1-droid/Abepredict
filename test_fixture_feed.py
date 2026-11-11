
import requests
import csv
import io
from datetime import datetime, date

url = "https://www.football-data.co.uk/fixtures.csv"

r = requests.get(url, timeout=30)
r.raise_for_status()

print("Download successful:", r.status_code)

reader = csv.DictReader(
    io.StringIO(r.content.decode("utf-8-sig"))
)

today = date.today()
count = 0

for row in reader:
    division = (row.get("Div") or "").strip()

    if division not in ["E1", "E2", "E3", "EC"]:
        continue

    raw_date = (row.get("Date") or "").strip()

    if not raw_date:
        continue

    match_date = None

    for fmt in ("%d/%m/%y", "%d/%m/%Y"):
        try:
            match_date = datetime.strptime(
                raw_date, fmt
            ).date()
            break
        except ValueError:
            pass

    if match_date and match_date >= today:
        count += 1
        print(
            division,
            raw_date,
            row.get("HomeTeam"),
            "vs",
            row.get("AwayTeam")
        )

print("\nUpcoming lower-league matches:", count)
