from playwright.sync_api import sync_playwright, Browser, Page
import json
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from config import COOKIES_FILE


def get_browser(playwright) -> tuple:
    browser = playwright.chromium.launch(
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
        ],
    )
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        locale="en-US",
    )

    # Patch navigator.webdriver to avoid detection
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        window.chrome = { runtime: {} };
    """)

    # Load saved cookies if available
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, encoding="utf-8") as f:
            cookies = json.load(f)
        context.add_cookies(cookies)

    page = context.new_page()
    return browser, context, page


def save_cookies(context):
    cookies = context.cookies()
    with open(COOKIES_FILE, "w", encoding="utf-8") as f:
        json.dump(cookies, f)
