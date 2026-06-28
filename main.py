import json
import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

print("Script starting...", flush=True)

# One call per (tab, page). Universe ~= 220 markets, ~14 API calls per full scan.
# At CHECK_INTERVAL_SECONDS=1 that's 14 req/sec from one IP → likely to hit rate
# limits. Bumping to 5–10s is usually fine if you trip 429s.
BASE_URL = "https://api.limitless.exchange/market-pages/988c7086-0b65-43a9-b8a1-2b71387a2b72/markets"
MARKET_URL = "https://limitless.exchange/markets/{slug}"
TABS = ["off-the-pitch", "player-props", "lineups", "transfers", "award-races", "underdogs"]
CHECK_INTERVAL_SECONDS = int(os.environ.get("CHECK_INTERVAL_SECONDS", "1"))
PAGE_LIMIT = 24
MAX_PAGES_PER_TAB = 10  # safety cap; today's largest tab needs 4
SEEN_FILE = os.environ.get("SEEN_FILE", "seen.json")

TELEGRAM_BOT_TOKEN = "8716981499:AAFCH2W5GybLsmWUZvYv08DjYRvx1Ieb7F8"
TELEGRAM_CHAT_ID = "5138327964"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://limitless.exchange/",
    "Origin": "https://limitless.exchange",
}

# Adaptive backoff state — multiplies CHECK_INTERVAL_SECONDS when we see 429/503.
_backoff_multiplier = 1
MAX_BACKOFF_MULT = 60


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


def fetch_tab(tab: str):
    """Fetch every page of one tab. Returns list of {slug,title,createdAt,tab}, or None on failure."""
    global _backoff_multiplier
    out = []
    for page in range(1, MAX_PAGES_PER_TAB + 1):
        params = {
            "football-tab": tab,
            "page": page,
            "limit": PAGE_LIMIT,
            "sort": "-createdAt",
        }
        try:
            r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
        except Exception as e:
            print(f"[{tab} p{page}] request error: {e}", flush=True)
            return None
        if r.status_code in (429, 503):
            _backoff_multiplier = min(_backoff_multiplier * 2, MAX_BACKOFF_MULT) if _backoff_multiplier > 1 else 4
            print(f"[{tab} p{page}] {r.status_code} — backoff x{_backoff_multiplier}", flush=True)
            return None
        if r.status_code >= 400:
            print(f"[{tab} p{page}] HTTP {r.status_code}", flush=True)
            return None
        items = r.json().get("data", []) or []
        for m in items:
            slug = m.get("slug") or ""
            if not slug:
                continue
            out.append({
                "slug":      slug,
                "title":     m.get("title") or m.get("question") or slug,
                "createdAt": m.get("createdAt") or "",
                "tab":       tab,
            })
        if len(items) < PAGE_LIMIT:
            break
    return out


def fetch_universe():
    """Fetch all tabs concurrently, dedup by slug. Returns None if any tab failed."""
    with ThreadPoolExecutor(max_workers=len(TABS)) as pool:
        results = list(pool.map(fetch_tab, TABS))
    if any(r is None for r in results):
        return None
    by_slug = {}
    for tab_markets in results:
        for m in tab_markets:
            # Keep first occurrence so the `tab` field tracks where we first saw it.
            by_slug.setdefault(m["slug"], m)
    return list(by_slug.values())


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
    global _backoff_multiplier
    print("Market Checker Started", flush=True)
    print(f"Polling every {CHECK_INTERVAL_SECONDS}s across {len(TABS)} tabs: {TABS}\n", flush=True)

    seen_ever = load_seen()
    first_run = not seen_ever
    if seen_ever:
        print(f"Loaded {len(seen_ever)} previously-seen slugs from {SEEN_FILE}", flush=True)

    while True:
        t0 = time.time()
        try:
            universe = fetch_universe()
            if universe is None:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] partial fetch failure, skipping cycle", flush=True)
            else:
                # Successful fetch → recover backoff
                if _backoff_multiplier > 1:
                    print(f"  recovered from backoff x{_backoff_multiplier}", flush=True)
                    _backoff_multiplier = 1
                current_slugs = {m["slug"] for m in universe}

                if first_run:
                    send_telegram(
                        f"Bot running. Seeded {len(current_slugs)} markets across {len(TABS)} tabs, watching for new ones."
                    )
                    seen_ever = set(current_slugs)
                    save_seen(seen_ever)
                    first_run = False
                else:
                    added = current_slugs - seen_ever
                    if added:
                        new_markets = [m for m in universe if m["slug"] in added]
                        new_markets.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
                        lines = [f"New Market{'s' if len(new_markets) > 1 else ''} Added!"]
                        for m in new_markets:
                            link = MARKET_URL.format(slug=m["slug"])
                            lines.append(f"+ [{m['tab']}] {m['title']}\n{link}")
                        send_telegram("\n\n".join(lines))
                        seen_ever.update(added)
                        save_seen(seen_ever)
                    else:
                        elapsed = time.time() - t0
                        print(
                            f"[{datetime.now().strftime('%H:%M:%S')}] no change ({len(current_slugs)} markets, {elapsed:.2f}s)",
                            flush=True,
                        )
        except Exception as e:
            print(f"Error: {e}", flush=True)

        sleep_for = CHECK_INTERVAL_SECONDS * _backoff_multiplier
        time.sleep(sleep_for)


if __name__ == "__main__":
    main()
