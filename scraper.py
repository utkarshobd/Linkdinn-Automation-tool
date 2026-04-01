import time
import logging
import requests
from bs4 import BeautifulSoup
from config import PORTFOLIO_URL, SCRAPE_DELAY

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _parse_companies(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    companies = []
    for card in soup.find_all("div", class_="notion-collection-card"):
        title_div = card.find("div", class_=lambda c: c and "notion-property__title" in c)
        if title_div:
            name = title_div.get_text(strip=True)
            if name and name not in companies:
                companies.append(name)
    return companies


def scrape_with_requests() -> list[str]:
    try:
        resp = requests.get(PORTFOLIO_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        companies = _parse_companies(resp.text)
        logger.info(f"Requests scraper found {len(companies)} candidates")
        return companies
    except Exception as e:
        logger.warning(f"Requests scraper failed: {e}")
        return []


def scrape_with_selenium() -> list[str]:
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By

        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument(f"user-agent={HEADERS['User-Agent']}")

        driver = webdriver.Chrome(options=opts)
        driver.get(PORTFOLIO_URL)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(SCRAPE_DELAY)
        html = driver.page_source
        driver.quit()

        companies = _parse_companies(html)
        logger.info(f"Selenium scraper found {len(companies)} candidates")
        return companies
    except Exception as e:
        logger.error(f"Selenium scraper failed: {e}")
        return []


def get_companies() -> list[str]:
    companies = scrape_with_requests()
    if len(companies) < 3:
        logger.info("Falling back to Selenium...")
        companies = scrape_with_selenium()
    return companies
