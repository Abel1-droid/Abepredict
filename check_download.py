import requests

urls = {
    "OpenFootball": "https://raw.githubusercontent.com/openfootball/england/master/2025-26/1-premierleague.csv",
    "Football-Data": "https://www.football-data.co.uk/mmz4281/2526/E0.csv"
}

for name, url in urls.items():
    try:
        r = requests.get(url, timeout=20)
        print("\n", name)
        print("Status:", r.status_code)
        print(r.text[:300])
    except Exception as e:
        print(name, "ERROR:", e)
