import time, requests
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

print("Script starting...", flush=True)

URL = "https://limitless.exchange/markets/page/football?rv=XBTEB9UCJF&football-fan=off-the-pitch&sort=ending_soon"
CHECK_INTERVAL_SECONDS = 10
TELEGRAM_BOT_TOKEN = "8716981499:AAFCH2W5GybLsmWUZvYv08DjYRvx1Ieb7F8"
TELEGRAM_CHAT_ID = "5138327964"
MARKET_CLASS = "css-pyffwl"
TITLE_CLASS = "chakra-text css-2d8e7c"

def get_markets():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,720")
    options.add_argument("--no-zygote")
    options.add_argument("--single-process")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-images")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    options.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    try:
        driver.get(URL)
        print("Waiting for markets to load...", flush=True)
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, MARKET_CLASS))
            )
        except:
            print("Timed out - scraping what is loaded", flush=True)
        time.sleep(2)
        html = driver.page_source
    finally:
        driver.quit()

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

    while True:
        try:
            ts = datetime.now().strftime('%H:%M:%S')
            print(f"[{ts}] Checking...", flush=True)
            titles = get_markets()

            if last_titles is None:
                send_telegram("Bot running")
                last_titles = set(titles)
            else:
                current = set(titles)
                added = current - last_titles
                if added:
                    msg = "New Market(s) Added!\n" + "\n".join(f"+ {t}" for t in added) + f"\n{URL}"
                    send_telegram(msg)
                else:
                    print("No change", flush=True)
                last_titles = current

        except Exception as e:
            print(f"Error: {e}", flush=True)

        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
