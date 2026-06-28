import json
import os
import time
import requests
from datetime import datetime

print("Script starting...", flush=True)

# sort=newest puts the freshest createdAt at the top — any new market lands
# on page 1 within seconds of creation instead of having to wait days for
# nearer-deadline markets to resolve and push it up the sort=deadline list.
BASE_URL = (
    "https://api.limitless.exchange/market-pages/"
    "988c7086-0b65-43a9-b8a1-2b71387a2b72/markets"
    "?football-fan=off-the-pitch&page={page}&limit=24&sort=newest"
)
MARKET_URL = "https://limitless.exchange/markets/{slug}"
CHECK_INTERVAL_SECONDS = 10
PAGES_PER_SCAN = 3  # 72 newest markets — covers slug backfills and any out-of-order creates
SEEN_FILE = os.environ.get("SEEN_FILE", "seen.json")

TELEGRAM_BOT_TOKEN = "8716981499:AAFCH2W5GybLsmWUZvYv08DjYRvx1Ieb7F8"
TELEGRAM_CHAT_ID = "5138327964"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://limitless.exchange/",
    "Origin": "https://limitless.exchange",
}


def load_seen() -> set:
    try:
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()
    except Exception as e:
        print(f"Could not read {SEEN_FILE}: {e}", flush=True)
        return set()


def save_seen(seen: set) -> None:
    try:
        tmp = SEEN_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(sorted(seen), f)
        os.replace(tmp, SEEN_FILE)
    except Exception as e:
        print(f"Could not write {SEEN_FILE}: {e}", flush=True)


def get_markets():
    markets = []
    for page in range(1, PAGES_PER_SCAN + 1):
        url = BASE_URL.format(page=page)
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        items = data.get("data", [])
        for m in items:
            title = m.get("title") or m.get("question") or m.get("slug") or ""
            slug = m.get("slug") or ""
            created = m.get("createdAt") or ""
            if title and slug:
                markets.append({"title": title, "slug": slug, "createdAt": created})
        if len(items) < 24:
            break
    print(f"Markets fetched (sort=newest, top {PAGES_PER_SCAN} pages): {len(markets)}", flush=True)
    if markets:
        print(f"  Newest: {markets[0]['createdAt']}  {markets[0]['title'][:70]}", flush=True)
    return markets


def send_telegram(message: str) -> None:
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "disable_web_page_preview": True},
            timeout=10,
        )
        if r.status_code == 200:
            print("Telegram sent", flush=True)
        else:
            print(f"Telegram error: {r.text}", flush=True)
    except Exception as e:
        print(f"Telegram error: {e}", flush=True)


def main():
    print("Market Checker Started", flush=True)
    print(f"Checking every {CHECK_INTERVAL_SECONDS}s, sort=newest, {PAGES_PER_SCAN} pages per scan\n", flush=True)

    seen_ever = load_seen()
    first_run = not seen_ever
    if seen_ever:
        print(f"Loaded {len(seen_ever)} previously-seen slugs from {SEEN_FILE}", flush=True)

    while True:
        try:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] Checking...", flush=True)
            markets = get_markets()
            current_slugs = {m["slug"] for m in markets}

            if first_run:
                # Don't spam every existing market on first run — just seed and announce.
                send_telegram(f"Bot running. Seeded {len(current_slugs)} existing markets, watching for new ones.")
                seen_ever = set(current_slugs)
                save_seen(seen_ever)
                first_run = False
            else:
                added_slugs = current_slugs - seen_ever
                if added_slugs:
                    new_markets = [m for m in markets if m["slug"] in added_slugs]
                    # Sort newest-first so the most recent shows up at the top of the message
                    new_markets.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
                    lines = [f"New Market{'s' if len(new_markets) > 1 else ''} Added!"]
                    for m in new_markets:
                        link = MARKET_URL.format(slug=m["slug"])
                        lines.append(f"+ {m['title']}\n{link}")
                    send_telegram("\n\n".join(lines))
                    seen_ever.update(added_slugs)
                    save_seen(seen_ever)
                else:
                    print("No change", flush=True)

        except Exception as e:
            print(f"Error: {e}", flush=True)

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
