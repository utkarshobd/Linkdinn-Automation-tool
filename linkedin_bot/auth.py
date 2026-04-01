import time
import random
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from playwright.sync_api import Page
from browser import save_cookies
from config import LINKEDIN_EMAIL, LINKEDIN_PASSWORD


def is_logged_in(page: Page) -> bool:
    try:
        page.goto("https://www.linkedin.com/feed/", timeout=20000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)
        # If redirected to login page, we are NOT logged in
        return "login" not in page.url and "authwall" not in page.url
    except Exception:
        return False


def login(page: Page) -> bool:
    print("[*] Navigating to LinkedIn login page...")

    # Clear stale cookies before fresh login
    if os.path.exists(COOKIES_FILE):
        os.remove(COOKIES_FILE)
        print("[*] Cleared old cookies")

    page.goto("https://www.linkedin.com/login", timeout=20000)
    page.wait_for_load_state("domcontentloaded")
    time.sleep(random.uniform(2, 3))

    # Wait for email field to be visible
    try:
        page.wait_for_selector("#username", timeout=10000)
    except Exception:
        print("[-] Login page did not load properly")
        return False

    print(f"[*] Filling email: {LINKEDIN_EMAIL}")
    page.click("#username")
    time.sleep(0.3)
    page.fill("#username", "")
    for char in LINKEDIN_EMAIL:
        page.type("#username", char, delay=random.randint(50, 120))
    time.sleep(random.uniform(0.5, 1.0))

    print("[*] Filling password...")
    page.click("#password")
    time.sleep(0.3)
    page.fill("#password", "")
    for char in LINKEDIN_PASSWORD:
        page.type("#password", char, delay=random.randint(50, 120))
    time.sleep(random.uniform(0.8, 1.5))

    print("[*] Clicking Sign in...")
    page.click("button[type='submit']")

    # Wait for navigation after login
    try:
        page.wait_for_url(lambda url: "feed" in url or "checkpoint" in url or "home" in url, timeout=15000)
    except Exception:
        # Check current URL manually
        time.sleep(5)

    current_url = page.url
    print(f"[*] After login URL: {current_url}")

    if "checkpoint" in current_url or "challenge" in current_url:
        print("[!] LinkedIn requires verification. Complete it manually in the browser window, then press Enter here.")
        input("Press Enter after completing verification: ")
        time.sleep(3)

    if "feed" in page.url or "mynetwork" in page.url or "jobs" in page.url:
        print("[+] Login successful!")
        return True

    print(f"[-] Login failed. Current URL: {page.url}")
    print("[-] Check your email/password in linkedin_bot/config.py")
    return False


def ensure_logged_in(page, context) -> bool:
    print("[*] Checking login status...")
    if is_logged_in(page):
        print("[+] Already logged in via cookies")
        return True
    print("[*] Not logged in, starting login flow...")
    success = login(page)
    if success:
        save_cookies(context)
        print("[+] Cookies saved for next run")
    return success
