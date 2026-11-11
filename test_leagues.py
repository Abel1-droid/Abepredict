
import requests

BASE = "https://www.football-data.co.uk/mmz4281"
LEAGUES = {
    "E1": "Championship",
    "E2": "League One",
    "E3": "League Two",
    "EC": "National League"
}

for code, name in LEAGUES.items():
    url = f"{BASE}/2627/{code}.csv"

    try:
        r = requests.get(url, timeout=20)
        print(f"\n{name}: HTTP {r.status_code}")

        if r.status_code == 200:
            lines = r.text.splitlines()
            print("CSV rows:", len(lines) - 1)
            print("Sample:", lines[1][:150] if len(lines) > 1 else "No matches yet")
        else:
            print("Not available at this address yet.")

    except Exception as e:
        print(name, "ERROR:", e)
