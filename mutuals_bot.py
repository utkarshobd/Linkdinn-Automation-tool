"""
mutuals_bot.py  (root folder)
──────────────────────────────
Standalone script — completely separate from bot.py / founders flow.

What it does:
1. Reads founders.csv (all rows, any status)
2. For each founder, visits their LinkedIn profile and scrapes mutual connections
3. Saves new mutuals to mutuals.csv (skips duplicates)
4. Sends a personalized message to each mutual that hasn't been messaged yet
"""

import csv
import os
import sys
import time
import random

# ── path setup so we can import linkedin_bot modules ──────────────────────────
_ROOT = os.path.dirname(os.path.abspath(__file__))
_BOT_DIR = os.path.join(_ROOT, "linkedin_bot")
sys.path.insert(0, _BOT_DIR)

from playwright.sync_api import sync_playwright
from browser import get_browser, save_cookies
from auth import ensure_logged_in
from mutuals_scraper import scrape_mutuals

# ── file paths ─────────────────────────────────────────────────────────────────
FOUNDERS_CSV = os.path.join(_ROOT, "founders.csv")
MUTUALS_CSV  = os.path.join(_ROOT, "mutuals.csv")

MUTUALS_FIELDS = ["name", "linkedin_url", "mutual_with", "message", "status"]

# Set to a founder name to process only that founder's mutuals
# Set to None to process ALL founders
TARGET_FOUNDER = None     

# ── message template for mutuals ───────────────────────────────────────────────
MUTUAL_MESSAGE_TEMPLATE = (
    "Hi {name}, I noticed we're both connected with {mutual_with}. "
    "I'd love to connect and know more about the work you're doing — "
    "always great to expand the network with people in the same circle!"
)


# ── CSV helpers ────────────────────────────────────────────────────────────────

def _load_founders() -> list[dict]:
    if not os.path.exists(FOUNDERS_CSV):
        print(f"[-] founders.csv not found at {FOUNDERS_CSV}")
        return []
    with open(FOUNDERS_CSV, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("linkedin_url")]


def _load_mutuals() -> list[dict]:
    if not os.path.exists(MUTUALS_CSV):
        return []
    with open(MUTUALS_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _save_mutuals(records: list[dict]):
    with open(MUTUALS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MUTUALS_FIELDS)
        writer.writeheader()
        writer.writerows(records)


def _append_mutuals(new_records: list[dict]):
    """Append only records whose linkedin_url isn't already in mutuals.csv."""
    existing = _load_mutuals()
    existing_urls = {r["linkedin_url"] for r in existing}

    added = 0
    file_exists = os.path.exists(MUTUALS_CSV)
    with open(MUTUALS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MUTUALS_FIELDS)
        if not file_exists:
            writer.writeheader()
        for rec in new_records:
            if rec["linkedin_url"] not in existing_urls:
                writer.writerow({k: rec.get(k, "") for k in MUTUALS_FIELDS})
                existing_urls.add(rec["linkedin_url"])
                added += 1
    return added


def _update_mutual_status(linkedin_url: str, new_status: str):
    records = _load_mutuals()
    for r in records:
        if r["linkedin_url"] == linkedin_url:
            r["status"] = new_status
    _save_mutuals(records)


# ── phase 1 — scrape mutuals from all founder profiles ────────────────────────

def run_scrape_mutuals(page):
    founders = _load_founders()
    if not founders:
        print("[-] No founders found in founders.csv")
        return

    if TARGET_FOUNDER:
        founders = [f for f in founders if f.get("founder_name", "").strip().lower() == TARGET_FOUNDER.strip().lower()]
        if not founders:
            print(f"[-] '{TARGET_FOUNDER}' not found in founders.csv")
            return

    print(f"[*] Scraping mutuals from {len(founders)} founder profiles...\n")
    total_added = 0

    for founder in founders:
        founder_name = founder.get("founder_name") or founder.get("company_name", "Unknown")
        founder_url  = founder["linkedin_url"]

        print(f"[→] {founder_name} — {founder_url}")
        try:
            mutuals = scrape_mutuals(page, founder_url, founder_name)
        except Exception as e:
            print(f"  [!] Unexpected error scraping {founder_name}: {e}")
            mutuals = []

        if mutuals:
            # Attach message and status before saving
            for m in mutuals:
                first_name = m["name"].split()[0] if m["name"] else "there"
                m["message"] = MUTUAL_MESSAGE_TEMPLATE.format(
                    name=first_name,
                    mutual_with=founder_name
                )
                m["status"] = "pending"

            added = _append_mutuals(mutuals)
            total_added += added
            print(f"  [✓] {added} new mutuals saved (skipped duplicates)\n")
        else:
            print(f"  [~] No mutuals found\n")

        time.sleep(random.uniform(5, 10))

    print(f"[✓] Scrape complete. {total_added} total new mutuals added to mutuals.csv\n")


# ── phase 2 — send messages to pending mutuals ────────────────────────────────

def run_send_messages(page, context):
    mutuals = _load_mutuals()
    pending = [m for m in mutuals if m.get("status") == "pending" and m.get("linkedin_url")]

    if not pending:
        print("[-] No pending mutuals to message.")
        return

    print(f"[*] Sending messages to {len(pending)} mutual connections...\n")

    for mutual in pending:
        name        = mutual["name"]
        url         = mutual["linkedin_url"]
        message     = mutual["message"]
        mutual_with = mutual["mutual_with"]

        print(f"[→] Messaging {name} (mutual with {mutual_with})")

        try:
            result = _send_message_to_mutual(page, url, message)
        except Exception as e:
            print(f"  [!] Unexpected error messaging {name}: {e}")
            result = "error"

        _update_mutual_status(url, result)
        print(f"  [status] {name} → {result}\n")

        time.sleep(random.uniform(20, 40))

    save_cookies(context)
    print("[✓] Messaging complete. Check mutuals.csv for statuses.")


def _send_message_to_mutual(page, linkedin_url: str, message: str) -> str:
    try:
        page.goto(linkedin_url, timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(random.uniform(3, 5))

        current_url = page.url
        title = page.title()
        if "404" in title or "Page Not Found" in title or "authwall" in current_url or "login" in current_url:
            print(f"  [!] Profile not accessible")
            return "not_found"

        page.evaluate("window.scrollBy(0, 300)")
        time.sleep(random.uniform(1, 2))

        # Find Message button
        msg_btn = None
        for btn in page.query_selector_all("button"):
            try:
                aria = btn.get_attribute("aria-label") or ""
                txt  = btn.inner_text().strip()
                if (txt == "Message" or "Message" in aria) and btn.is_visible():
                    msg_btn = btn
                    break
            except Exception:
                continue

        if not msg_btn:
            print(f"  [!] Message button not found — may not be connected")
            return "not_connected"

        msg_btn.scroll_into_view_if_needed()
        time.sleep(random.uniform(1, 2))
        msg_btn.click()
        time.sleep(random.uniform(3, 4))

        # Type message in chat box
        try:
            page.wait_for_selector("div.msg-form__contenteditable", timeout=8000)
            msg_box = page.query_selector("div.msg-form__contenteditable")
            if not msg_box:
                print(f"  [!] Message box not found")
                return "error"
            msg_box.click()
            time.sleep(random.uniform(0.5, 1))
            for char in message:
                msg_box.type(char, delay=random.randint(40, 100))
            time.sleep(random.uniform(2, 3))
        except Exception as e:
            print(f"  [!] Could not type message: {e}")
            return "error"

        # Click Send
        for sel in ["button.msg-form__send-button", "button[aria-label='Send']", "button:has-text('Send')"]:
            try:
                send_btn = page.query_selector(sel)
                if send_btn and send_btn.is_visible():
                    time.sleep(random.uniform(1, 2))
                    send_btn.click()
                    time.sleep(random.uniform(2, 3))
                    print(f"  [✓] Message sent!")
                    return "messaged"
            except Exception:
                continue

        print(f"  [!] Send button not found")
        return "error"

    except Exception as e:
        print(f"  [!] Error in _send_message_to_mutual: {e}")
        return "error"


# ── main ───────────────────────────────────────────────────────────────────────

def run():
    with sync_playwright() as p:
        browser, context, page = get_browser(p)

        if not ensure_logged_in(page, context):
            print("[-] Login failed. Exiting.")
            browser.close()
            return

        save_cookies(context)

        # Phase 1 — scrape mutual connections from all founder profiles
        run_scrape_mutuals(page)

        # Phase 2 — send messages to all pending mutuals
        run_send_messages(page, context)

        browser.close()

    print("\n[✓] Done. Check mutuals.csv for full results.")


if __name__ == "__main__":
    run()
