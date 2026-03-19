import time, requests
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

print("Script starting...", flush=True)

URL = "https://limitless.exchange/markets/page/football?rv=XBTEB9UCJF&football-fan=off-the-pitch&sort=ending_soon"
CHECK_INTERVAL_SECONDS = 10
TELEGRAM_BOT_TOKEN = "8716981499:AAFCH2W5GybLsmWUZvYv08DjYRvx1Ieb7F8"
TELEGRAM_CHAT_ID = "5138327964"
MARKET_CLASS = "css-pyffwl"
TITLE_CLASS = "chakra-text css-2d8e7c"

def get_markets():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)
        try:
            page.wait_for_selector(f".{MARKET_CLASS}", timeout=15000)
        except:
            print("Timed out waiting for markets", flush=True)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    cards = [div for div in soup.find_all("div") if MARKET_CLASS in div.get("class", [])]
    print(f"Markets found: {len(cards)}", flush=True)

    titles = []
    for card in cards[:20]:
        p = card.find("p", class_=TITLE_CLASS)
        if p:
            titles.append(p.get_text(strip=True))

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
                    msg = "New Market(s) Added!\n" + "\n".join(f"+ {t}" for t in added) + f"\n{URL}"
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
