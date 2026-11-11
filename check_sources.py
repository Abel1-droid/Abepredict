
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import urllib.robotparser

BASE = "https://www.footballpyramids.com"
URL = BASE + "/england/"

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; FootballResearch/1.0)"
}

try:
    robots = urllib.robotparser.RobotFileParser()
    robots.set_url(BASE + "/robots.txt")
    robots.read()

    if not robots.can_fetch(headers["User-Agent"], URL):
        print("Robots.txt does not permit this page to be fetched.")
        raise SystemExit

    response = requests.get(URL, headers=headers, timeout=20)
    print("HTTP status:", response.status_code)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    print("Page title:", soup.title.get_text(strip=True) if soup.title else "No title")
    print("Tables found:", len(soup.find_all("table")))

    print("\nCompetition links:")
    for link in soup.find_all("a", href=True):
        label = link.get_text(" ", strip=True)
        href = urljoin(BASE, link["href"])

        if "fixtures" in href.lower() or "results" in href.lower():
            print(label, "->", href)

    print("\nPage text preview:")
    print(soup.get_text(" ", strip=True)[:1500])

except Exception as error:
    print("ERROR:", error)
