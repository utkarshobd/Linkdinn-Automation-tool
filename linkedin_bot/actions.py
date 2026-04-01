import time
import random
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from playwright.sync_api import Page


def _delay(a=4, b=5):
    time.sleep(random.uniform(a, b))


def send_connection(page: Page, linkedin_url: str, message: str) -> str:
    try:
        print(f"  [→] Opening profile: {linkedin_url}")
        page.goto(linkedin_url, timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        _delay(4, 6)

        # Check for 404 or redirect
        current_url = page.url
        title = page.title()
        if "404" in title or "Page Not Found" in title or "authwall" in current_url or "login" in current_url:
            print(f"  [!] Profile not found or not accessible: {current_url}")
            return "not_found"

        page.evaluate("window.scrollBy(0, 350)")
        _delay(2, 3)
        page.evaluate("window.scrollBy(0, -150)")
        _delay(2, 3)

        connect_btn = _find_connect_button(page)

        if connect_btn is None:
            print("  [!] Connect button not found")
            return "no_connect_button"

        if connect_btn in ("already_connected", "already_pending"):
            return connect_btn

        print("  [*] Scrolling to Connect button...")
        connect_btn.scroll_into_view_if_needed()
        _delay(2, 3)

        print("  [*] Clicking Connect/Add...")
        connect_btn.click()
        _delay(3, 5)

        return _handle_connect_modal(page, message)

    except Exception as e:
        print(f"  [!] Error in send_connection: {e}")
        return "error"


def _find_connect_button(page: Page):
    _delay(1, 2)

    # Check if already pending — look only in profile actions area
    profile_actions = page.query_selector(".pvs-profile-actions, .pv-top-card__actions, div.ph5")

    if profile_actions:
        for btn in profile_actions.query_selector_all("button"):
            try:
                txt = btn.inner_text().strip()
                if "Pending" in txt and btn.is_visible():
                    print("  [~] Connection request already pending — skipping")
                    return "already_pending"
            except Exception:
                continue

        # Check direct Connect button inside profile actions only
        for btn in profile_actions.query_selector_all("button"):
            try:
                aria = btn.get_attribute("aria-label") or ""
                if "to connect" in aria and btn.is_visible():
                    print(f"  [✓] Found Connect button in profile actions: aria='{aria}'")
                    return btn
            except Exception:
                continue

        # Click More inside profile actions only
        try:
            more_btn = None
            for btn in profile_actions.query_selector_all("button"):
                try:
                    aria = btn.get_attribute("aria-label") or ""
                    if "More actions" in aria and btn.is_visible():
                        more_btn = btn
                        break
                except Exception:
                    continue

            if more_btn:
                print("  [*] Clicking More dropdown...")
                more_btn.click()
                _delay(2, 3)

                # Scope to the dropdown that just opened
                dropdown = page.query_selector("div.artdeco-dropdown__content--is-open, div[data-test-overflow-menu-dropdown]")
                search_root = dropdown if dropdown else page

                for li in search_root.query_selector_all("li"):
                    try:
                        span = li.query_selector("span.display-flex")
                        txt = span.inner_text().strip() if span else li.inner_text().strip()
                        if txt in ("Add", "Connect") and li.is_visible():
                            print(f"  [✓] Found '{txt}' in More dropdown")
                            return li
                    except Exception:
                        continue
        except Exception as e:
            print(f"  [!] More dropdown error: {e}")

        # Check if already connected inside profile actions
        for btn in profile_actions.query_selector_all("button"):
            try:
                txt = btn.inner_text().strip()
                aria = btn.get_attribute("aria-label") or ""
                if (txt == "Message" or "Message" in aria) and btn.is_visible():
                    print("  [~] Already connected — Message button found")
                    return "already_connected"
            except Exception:
                continue

    print("  [!] Profile actions section not found")
    return None


def _handle_connect_modal(page: Page, message: str) -> str:
    # Some profiles skip the modal and send directly
    # Wait up to 5 seconds for modal
    try:
        page.wait_for_selector("div[role='dialog']", timeout=5000)
    except Exception:
        # No modal — request may have been sent directly
        print("  [~] No modal — checking if sent directly...")
        _delay(2, 3)
        # Check if Pending button now visible = sent successfully
        for btn in page.query_selector_all("button"):
            try:
                if "Pending" in btn.inner_text().strip() and btn.is_visible():
                    print("  [✓] Connection request sent (no modal)!")
                    return "sent"
            except Exception:
                continue
        return "error"

    _delay(2, 3)

    # Send without note
    for sel in ["button:has-text('Send')", "button:has-text('Send now')", "button:has-text('Done')"]:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                print("  [*] Clicking Send...")
                _delay(1, 2)
                btn.click()
                _delay(3, 4)
                print("  [✓] Connection request sent!")
                return "sent"
        except Exception:
            continue

    print("  [!] Send button not found")
    return "error"


def send_message(page: Page, linkedin_url: str, message: str) -> str:
    try:
        print(f"  [→] Opening profile to message: {linkedin_url}")
        page.goto(linkedin_url, timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        _delay(4, 6)

        msg_btn = None
        for btn in page.query_selector_all("button"):
            try:
                aria = btn.get_attribute("aria-label") or ""
                txt = btn.inner_text().strip()
                if (txt == "Message" or "Message" in aria) and btn.is_visible():
                    msg_btn = btn
                    break
            except Exception:
                continue

        if not msg_btn:
            print("  [!] Message button not found — not connected yet?")
            return "not_connected"

        print("  [*] Clicking Message button...")
        msg_btn.scroll_into_view_if_needed()
        _delay(2, 3)
        msg_btn.click()
        _delay(3, 4)

        try:
            page.wait_for_selector("div.msg-form__contenteditable", timeout=8000)
            msg_box = page.query_selector("div.msg-form__contenteditable")
            if msg_box:
                msg_box.click()
                _delay(1, 2)
                for char in message:
                    msg_box.type(char, delay=random.randint(40, 100))
                _delay(2, 3)
        except Exception as e:
            print(f"  [!] Could not type message: {e}")
            return "error"

        for sel in ["button.msg-form__send-button", "button[aria-label='Send']", "button:has-text('Send')"]:
            try:
                send_btn = page.query_selector(sel)
                if send_btn and send_btn.is_visible():
                    _delay(1, 2)
                    send_btn.click()
                    _delay(3, 4)
                    print("  [✓] Message sent!")
                    return "messaged"
            except Exception:
                continue

        print("  [!] Could not find message Send button")
        return "error"

    except Exception as e:
        print(f"  [!] Error in send_message: {e}")
        return "error"


def is_connected(page: Page, linkedin_url: str) -> bool:
    try:
        page.goto(linkedin_url, timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        _delay(3, 4)
        for btn in page.query_selector_all("button"):
            try:
                txt = btn.inner_text().strip()
                aria = btn.get_attribute("aria-label") or ""
                if (txt == "Message" or "Message" in aria) and btn.is_visible():
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False
