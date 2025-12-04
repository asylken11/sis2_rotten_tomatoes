"""
Scraper for Rotten Tomatoes (movies browse pages).
Saves raw JSON to data/raw.json.

Usage:
    python src/scraper.py
"""
import re
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

BASE_URL = os.getenv("BASE_URL", "https://www.rottentomatoes.com/browse/movies_in_theaters")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./data"))
RAW_JSON = Path(os.getenv("RAW_JSON", "./data/raw.json"))
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
SCROLL_WAIT_SECONDS = float(os.getenv("SCROLL_WAIT_SECONDS", 2))
MAX_SCROLL_PAUSES = int(os.getenv("MAX_SCROLL_PAUSES", 6))
MAX_ITEMS = int(os.getenv("MAX_ITEMS", 500))

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def create_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service("chromedriver/chromedriver.exe")

    driver = webdriver.Chrome(service=service, options=options)
    driver.set_window_size(1920, 1080)

    return driver

def maybe_click_load_more(driver):
    """If there's a 'Load More' button, click it. Return True if clicked."""
    try:
        # safer: find_elements возвращает список (пустой, если не найдено)
        buttons = driver.find_elements(By.CSS_SELECTOR, "button.js-load-more")
        if buttons:
            btn = buttons[0]
            if btn.is_displayed():
                try:
                    btn.click()
                    return True
                except Exception:
                    return False
    except Exception:
        # на всякий случай не ломаем основной цикл
        return False
    return False


def infinite_scroll(driver):
    """
    Scrolls down until content stops loading. Uses a pause counter to avoid infinite loops.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    pauses = 0

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_WAIT_SECONDS)

        # optionally click load more
        maybe_click_load_more(driver)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            pauses += 1
            if pauses >= MAX_SCROLL_PAUSES:
                break
        else:
            pauses = 0
            last_height = new_height


def safe_text(elem):
    try:
        txt = elem.text
        return txt.strip()
    except Exception:
        return None

def get_movie_cards(driver):
    # ждем пока прогрузится список
    WebDriverWait(driver, 15).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.js-tile-link"))
    )
    return driver.find_elements(By.CSS_SELECTOR, "div.js-tile-link")

def extract_movie_data(driver, card):
    # title + url
    try:
        a = card.find_element(By.CSS_SELECTOR, "a[data-qa='discovery-media-list-item-caption']")
        url = a.get_attribute("href")
        title = a.find_element(By.CSS_SELECTOR, "span[data-qa='discovery-media-list-item-title']").text.strip()
    except:
        url = None
        title = None

    # date
    try:
        date = a.find_element(By.CSS_SELECTOR, "span[data-qa='discovery-media-list-item-start-date']").text.strip()
    except:
        date = None

    # poster: shadow-root
    poster = None
    try:
        rtimg = card.find_element(By.CSS_SELECTOR, "rt-img")
        shadow_root = driver.execute_script("return arguments[0].shadowRoot", rtimg)
        img = shadow_root.find_element(By.CSS_SELECTOR, "img")
        poster = img.get_attribute("src")
    except:
        pass

    # year из даты
    year = None
    if date:
        # Пример: 'Opened Dec 03, 2025'
        year = date.split(',')[-1].strip()

    return {
        "title": title,
        "url": url,
        "poster": poster,
        "release_date": date,
        "year": year,
        "tomatometer": None,
        "audience_score": None,
    }

def scrape_list(driver, base_url):
    driver.get(base_url)
    cards = get_movie_cards(driver)

    movies = []
    for card in cards:
        movie = extract_movie_data(driver, card)
        movies.append(movie)
    return movies

def parse_card(card):
    # movie URL
    try:
        link = card.get_attribute("href")
    except:
        link = None

    # title
    try:
        title = card.find_element(
            By.CSS_SELECTOR,
            '[data-qa="discovery-media-list-item-title"]'
        ).text.strip()
    except:
        title = None

    # poster
    try:
        poster = card.find_element(
            By.CSS_SELECTOR,
            '[data-qa="discovery-media-list-item-poster"] img'
        ).get_attribute("src")
    except:
        poster = None

    # tomatometer
    try:
        score = card.find_element(By.TAG_NAME, "score-presentation")
        tomatometer = score.get_attribute("tomatometer")
        audience = score.get_attribute("audiencescore")
    except:
        tomatometer = None
        audience = None

    # release_year (optional)
    release_year = None
    if title:
        m = re.search(r"\((\d{4})\)", title)
        if m:
            release_year = m.group(1)
            title = title.replace(f"({release_year})", "").strip()

    return {
        "title": title,
        "movie_url": link,
        "poster_url": poster,
        "tomatometer": tomatometer,
        "audience_score": audience,
        "release_year": release_year
    }



def main():
    print("Starting scraper...")
    driver = create_driver()
    try:
        driver.get(BASE_URL)
        # wait for main discovery container (best-effort)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-qa="discovery-media-list"]'))
            )
        except TimeoutException:
            # proceed anyway — some pages may render differently
            pass

        # scroll to load items
        infinite_scroll(driver)

        # find cards
        # primary selector:
        cards = driver.find_elements(By.CSS_SELECTOR, '[data-qa="discovery-media-list-item"]')
        if not cards:
            # fallback: detect likely card wrappers
            cards = driver.find_elements(By.CSS_SELECTOR, '.js-store .col-sm-12, .mb-movie, .movie_info')
        print(f"Found {len(cards)} card elements (raw)")

        data = []
        for c in cards:
            if len(data) >= MAX_ITEMS:
                break
            try:
                item = parse_card(c)
                # only append if at least title present
                if item.get("title"):
                    data.append(item)
            except Exception as e:
                print("Card parse error:", e)

        # write to RAW_JSON
        with open(RAW_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Scraping finished — wrote {len(data)} records to {RAW_JSON}")

    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
