import sys
import os
import csv
import time
import random

_BOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BOT_DIR)

from playwright.sync_api import sync_playwright
from browser import get_browser, save_cookies
from auth import ensure_logged_in
from actions import send_connection, send_message, is_connected
from logger import can_send_today, record_sent, get_today_count
from config import CSV_INPUT, MAX_CONNECTS_PER_DAY

FOLLOWUP_MESSAGE = (
    "Hi {name}, thanks for connecting! "
    "I've been following what {company} is building and would love to learn more. "
    "Would you be open to a quick chat?"
)


def load_by_status(status: str) -> list[dict]:
    if not os.path.exists(CSV_INPUT):
        print(f"[-] CSV not found: {CSV_INPUT}")
        return []
    with open(CSV_INPUT, newline="", encoding="utf-8") as f:
        # Also retry no_connect_button and error statuses
        retry = {"pending", "no_connect_button", "error"}
        if status == "pending":
            return [r for r in csv.DictReader(f) if r["status"] in retry and r["linkedin_url"]]
        return [r for r in csv.DictReader(f) if r["status"] == status and r["linkedin_url"]]


def update_status(linkedin_url: str, new_status: str):
    rows = []
    with open(CSV_INPUT, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row["linkedin_url"] == linkedin_url:
                row["status"] = new_status
            rows.append(row)
    with open(CSV_INPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_connect(page, context):
    """Send connection requests to all pending profiles."""
    pending = load_by_status("pending")
    if not pending:
        print("[-] No pending profiles found.")
        return

    remaining = MAX_CONNECTS_PER_DAY - get_today_count()
    if remaining <= 0:
        print(f"[-] Daily limit of {MAX_CONNECTS_PER_DAY} reached. Run again tomorrow.")
        return

    to_process = pending[:remaining]
    print(f"[*] {len(pending)} pending | Sending up to {remaining} today\n")

    for record in to_process:
        if not can_send_today():
            print(f"[!] Daily limit reached. Stopping.")
            break

        name = record["founder_name"]
        url = record["linkedin_url"]
        message = record["message"]

        print(f"[→] {name} — {record['company_name']}")
        result = send_connection(page, url, message)

        if result == "sent":
            update_status(url, "requested")
            record_sent(url, name)
        elif result == "already_connected":
            update_status(url, "already_connected")
            print(f"  [~] {name} is already a connection — skipping")
        elif result == "already_pending":
            update_status(url, "requested")
            print(f"  [~] {name} already has a pending request")
        elif result == "not_found":
            update_status(url, "not_found")
            print(f"  [!] {name} profile URL is wrong — update founders.csv manually")
        elif result == "no_connect_button":
            update_status(url, "no_connect_button")
        else:
            update_status(url, "error")

        wait = random.uniform(30, 60)
        print(f"  [~] Waiting {wait:.0f}s before next...\n")
        time.sleep(wait)

    save_cookies(context)


def run_followup(page, context):
    """
    Check all 'requested' profiles.
    If accepted (Message button visible) → send follow-up message.
    """
    requested = load_by_status("requested")
    if not requested:
        print("[-] No requested profiles to check.")
        return

    print(f"[*] Checking {len(requested)} requested profiles for acceptance...\n")

    for record in requested:
        name = record["founder_name"]
        url = record["linkedin_url"]
        company = record["company_name"]

        print(f"[?] Checking if {name} accepted...")

        if is_connected(page, url):
            print(f"  [✓] {name} accepted! Sending follow-up message...")
            update_status(url, "accepted")

            msg = FOLLOWUP_MESSAGE.format(
                name=name.split()[0],
                company=company
            )
            result = send_message(page, url, msg)

            if result == "messaged":
                update_status(url, "messaged")
            else:
                update_status(url, "accepted")  # keep as accepted, retry later
        else:
            print(f"  [~] {name} hasn't accepted yet — keeping as requested")

        wait = random.uniform(15, 30)
        print(f"  [~] Waiting {wait:.0f}s...\n")
        time.sleep(wait)

    save_cookies(context)


def run():
    with sync_playwright() as p:
        browser, context, page = get_browser(p)

        if not ensure_logged_in(page, context):
            browser.close()
            return

        save_cookies(context)
        run_connect(page, context)
        run_followup(page, context)
        browser.close()

    print("\n[✓] Done. Check founders.csv for updated statuses.")


if __name__ == "__main__":
    run()
