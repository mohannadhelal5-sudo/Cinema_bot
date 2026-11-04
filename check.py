import os, sys, json, re
from urllib.parse import urljoin, urlparse
import requests
from playwright.sync_api import sync_playwright

URL = "https://egy.voxcinemas.com/showtimes?c=city-centre-almaza"   # حط هنا نفس الرابط اللي كنت مستخدمه
TOKEN = os.environ["TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
FILE = "seen.json"
SKIP = {"whatson", "comingsoon", "coming-soon", "all"}


def fetch_movies():
    movies = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        ctx = browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
            locale="en-US",
            viewport={"width": 1366, "height": 900},
        )
        page = ctx.new_page()

        for attempt in range(3):
            try:
                page.goto(URL, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(5000)          # استنى الجافاسكريبت يحمّل الأفلام
                page.mouse.wheel(0, 4000)            # سكرول عشان أي lazy loading
                page.wait_for_timeout(2000)
                break
            except Exception as e:
                print(f"محاولة {attempt + 1} فشلت:", e)
                if attempt == 2:
                    page.screenshot(path="debug.png")
                    browser.close()
                    return {}

        links = page.eval_on_selector_all(
            'a[href*="/movies/"]',
            "els => els.map(a => ({href: a.getAttribute('href'),"
            " text: (a.getAttribute('title') || a.innerText || '').trim()}))",
        )
        print("الصفحة:", page.title(), "| عدد اللينكات:", len(links))
        browser.close()

    for l in links:
        path = urlparse(urljoin(URL, l["href"])).path.rstrip("/")
        m = re.fullmatch(r"/movies/([^/]+)", path)
        if not m or m.group(1) in SKIP:
            continue
        name = l["text"].split("\n")[0].strip() or m.group(1).replace("-", " ").title()
        href = urljoin(URL, path)
        # لو الاسم اتسجل قبل كده باسم فاضي نحدّثه
        if href not in movies or len(name) > len(movies[href]):
            movies[href] = name
    return movies


movies = fetch_movies()
print("لقيت", len(movies), "فيلم")
if not movies:
    print("مفيش أفلام اتقرأت")
    sys.exit(1)

seen = set(json.load(open(FILE))) if os.path.exists(FILE) else None

if seen is not None:
    for href in movies.keys() - seen:
        requests.get(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            params={"chat_id": CHAT_ID, "text": f"🎬 فيلم جديد نزل:\n{movies[href]}\n{href}"},
            timeout=20,
        )

json.dump(sorted((seen or set()) | set(movies)), open(FILE, "w"), ensure_ascii=False)
