import time, requests
from datetime import datetime

print("Script starting...", flush=True)

BASE_URL = "https://api.limitless.exchange/market-pages/988c7086-0b65-43a9-b8a1-2b71387a2b72/markets?football-fan=off-the-pitch&page={page}&limit=24&sort=deadline"
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
    titles = []
    for page in range(1, 3):  # fetch page 1 and page 2
        url = BASE_URL.format(page=page)
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        markets = data.get("data", [])
        for m in markets:
            title = m.get("title") or m.get("question") or m.get("slug") or ""
            if title:
                titles.append(title)
        if len(markets) < 24:  # no more pages
            break
    titles = titles[:35]  # cap at 35
    print(f"Markets found: {len(titles)}", flush=True)
    print(f"Titles: {titles[:3]}", flush=True)
    return titles

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
    last_titles = None
    seen_ever = set()

    while True:
        try:
            ts = datetime.now().strftime('%H:%M:%S')
            print(f"[{ts}] Checking...", flush=True)
            titles = get_markets()

            if last_titles is None:
                send_telegram("Bot running")
                last_titles = set(titles)
                seen_ever = set(titles)
            else:
                current = set(titles)
                added = current - seen_ever
                if added:
                    msg = "New Market(s) Added!\n" + "\n".join(f"+ {t}" for t in added) + f"\nhttps://limitless.exchange/markets/page/football?rv=XBTEB9UCJF&football-fan=off-the-pitch&sort=ending_soon"
                    send_telegram(msg)
                    seen_ever.update(added)
                else:
                    print("No change", flush=True)
                last_titles = current

        except Exception as e:
            print(f"Error: {e}", flush=True)

        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
