import json
import os
import sys
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

URL = "https://egy.voxcinemas.com/showtimes?c=city-centre-almaza"  # أو رابط موقع السينما الخاص بك
TOKEN = os.environ["TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
FILE = "seen.json"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL, timeout=60000)
    page.wait_for_timeout(5000)  # انتظار تحميل الصفحة بالكامل
    html = page.content()
    browser.close()

from bs4 import BeautifulSoup
soup = BeautifulSoup(html, "html.parser")

movies = {}
for a in soup.select('a[href*="/movie-details/"]'):
    name = a.get("title") or a.get_text(strip=True)
    if name:
        movies[a.get("href")] = name

print(f"لقيت {len(movies)} فيلم")

if not movies:
    print("مفيش أفلام اتقرات")
    sys.exit()

seen = set(json.load(open(FILE))) if os.path.exists(FILE) else None

if seen is not None:
    for href in movies.keys() - seen:
        requests_lib = __import__('requests')
        requests_lib.get(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            params={
                "chat_id": CHAT_ID,
                "text": f"فيلم جديد نزل : {movies[href]}\n{urljoin(URL, href)}"
            },
        )

json.dump(sorted((seen or set()) | set(movies)), open(FILE, "w"), ensure_ascii=False)
