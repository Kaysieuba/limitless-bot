import time, requests
from datetime import datetime

print("Script starting...", flush=True)

BASE_URL = "https://api.limitless.exchange/market-pages/988c7086-0b65-43a9-b8a1-2b71387a2b72/markets?football-fan=off-the-pitch&page={page}&limit=24&sort=deadline"
MARKET_URL = "https://limitless.exchange/markets/{slug}"
CHECK_INTERVAL_SECONDS = 10
TELEGRAM_BOT_TOKEN = "8716981499:AAFCH2W5GybLsmWUZvYv08DjYRvx1Ieb7F8"
TELEGRAM_CHAT_ID = "5138327964"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://limitless.exchange/",
    "Origin": "https://limitless.exchange"
}

def get_markets():
    markets = []
    for page in range(1, 3):
        url = BASE_URL.format(page=page)
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        items = data.get("data", [])
        for m in items:
            title = m.get("title") or m.get("question") or m.get("slug") or ""
            slug = m.get("slug") or ""
            if title and slug:
                markets.append({"title": title, "slug": slug})
        if len(items) < 24:
            break
    markets = markets[:35]
    print(f"Markets found: {len(markets)}", flush=True)
    print(f"First: {markets[0]['title'] if markets else 'none'}", flush=True)
    return markets

def send_telegram(message):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message},
            timeout=10
        )
        if r.status_code == 200:
            print("Telegram sent", flush=True)
        else:
            print(f"Telegram error: {r.text}", flush=True)
    except Exception as e:
        print(f"Error: {e}", flush=True)

def main():
    print("Market Checker Started", flush=True)
    print(f"Checking every {CHECK_INTERVAL_SECONDS}s\n", flush=True)
    last_slugs = None
    seen_ever = set()

    while True:
        try:
            ts = datetime.now().strftime('%H:%M:%S')
            print(f"[{ts}] Checking...", flush=True)
            markets = get_markets()
            current_slugs = {m["slug"] for m in markets}

            if last_slugs is None:
                send_telegram("Bot running")
                last_slugs = current_slugs
                seen_ever = current_slugs.copy()
            else:
                added_slugs = current_slugs - seen_ever
                if added_slugs:
                    new_markets = [m for m in markets if m["slug"] in added_slugs]
                    lines = ["New Market(s) Added!"]
                    for m in new_markets:
                        link = MARKET_URL.format(slug=m["slug"])
                        lines.append(f"+ {m['title']}\n{link}")
                    send_telegram("\n\n".join(lines))
                    seen_ever.update(added_slugs)
                else:
                    print("No change", flush=True)
                last_slugs = current_slugs

        except Exception as e:
            print(f"Error: {e}", flush=True)

        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
