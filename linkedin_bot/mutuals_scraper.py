import re
import time
import random
from playwright.sync_api import Page


def _delay(a=2, b=4):
    time.sleep(random.uniform(a, b))


def scrape_mutuals(page: Page, founder_url: str, founder_name: str) -> list[dict]:
    """
    Visit a founder's LinkedIn profile, click the mutual connections link,
    and scrape name + profile URL of each mutual.
    Returns list of dicts: {name, linkedin_url, mutual_with}
    """
    try:
        print(f"  [→] Opening profile for mutuals: {founder_url}")
        page.goto(founder_url, timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        _delay(3, 5)

        current_url = page.url
        title = page.title()
        if "404" in title or "Page Not Found" in title or "authwall" in current_url or "login" in current_url:
            print(f"  [!] Profile not accessible: {current_url}")
            return []

        page.evaluate("window.scrollBy(0, 300)")
        _delay(2, 3)
        page.evaluate("window.scrollBy(0, 300)")
        _delay(1, 2)

        # Debug — print all text that contains 'mutual' so we can see real HTML
        mutual_texts = page.evaluate("""
            () => {
                const results = [];
                document.querySelectorAll('*').forEach(el => {
                    if (el.children.length === 0 && el.innerText && el.innerText.toLowerCase().includes('mutual')) {
                        results.push({
                            tag: el.tagName,
                            cls: el.className,
                            text: el.innerText.trim().substring(0, 120),
                            parentTag: el.parentElement ? el.parentElement.tagName : '',
                            parentCls: el.parentElement ? el.parentElement.className.substring(0, 80) : ''
                        });
                    }
                });
                return results;
            }
        """)
        if mutual_texts:
            print(f"  [debug] Found {len(mutual_texts)} elements with 'mutual' text:")
            for m in mutual_texts:
                print(f"    tag={m['tag']} cls='{m['cls']}' parent={m['parentTag']} parentCls='{m['parentCls']}'")
                print(f"    text: {m['text']}")
        else:
            print(f"  [debug] No elements with 'mutual' text found on page")

        # Find the mutual connections link — LinkedIn renders it as an anchor
        # Text looks like: "Gaurav, Paras and 4 other mutual connections"
        mutual_link = None
        for selector in [
            "a[href*='facetNetwork']",
            "a:has-text('mutual connection')",
            "span:has-text('mutual connection')",
            "button:has-text('mutual connection')",
            "*:has-text('mutual connection')",
        ]:
            try:
                el = page.query_selector(selector)
                if el and el.is_visible():
                    mutual_link = el
                    print(f"  [✓] Found mutual connections element via: {selector}")
                    break
            except Exception:
                continue

        if not mutual_link:
            print(f"  [~] No mutual connections found for {founder_name}")
            return []

        # Get count from text like "Gaurav, Paras and 4 other mutual connections"
        raw_text = mutual_link.inner_text().strip()
        print(f"  [i] Mutual text: '{raw_text}'")

        mutual_link.click()
        _delay(3, 5)

        # After click, LinkedIn opens a modal or navigates to a connections page
        # Wait for profile cards to appear
        mutuals = []

        # Try modal first
        try:
            page.wait_for_selector("div.artdeco-modal__content, div[data-test-modal]", timeout=6000)
            print("  [*] Modal opened, scraping mutuals...")
            mutuals = _scrape_from_modal(page, founder_name)
        except Exception:
            # No modal — may have navigated to a page
            print("  [*] No modal, trying page scrape...")
            _delay(3, 5)

            # Debug — dump all anchor tags with /in/ visible on page
            debug_links = page.evaluate("""
                () => {
                    const results = [];
                    document.querySelectorAll('a[href*="/in/"]').forEach(el => {
                        const href = el.getAttribute('href') || '';
                        const text = el.innerText.trim().substring(0, 80);
                        const cls  = el.className.substring(0, 80);
                        const parentCls = el.parentElement ? el.parentElement.className.substring(0, 80) : '';
                        results.push({ href, text, cls, parentCls });
                    });
                    return results.slice(0, 20);
                }
            """)
            print(f"  [debug] /in/ links found on page after click ({len(debug_links)}):")
            for d in debug_links:
                print(f"    href={d['href']}  text='{d['text']}'  cls='{d['cls']}'  parentCls='{d['parentCls']}'")

            # Debug — dump all li/div tags that might be result cards
            debug_cards = page.evaluate("""
                () => {
                    const selectors = [
                        'li.reusable-search__result-container',
                        'li.mn-connection-card',
                        'div.entity-result',
                        'li[class*="result"]',
                        'div[class*="result"]',
                        'li[class*="connection"]',
                        'div[class*="connection"]'
                    ];
                    const found = {};
                    selectors.forEach(sel => {
                        found[sel] = document.querySelectorAll(sel).length;
                    });
                    return found;
                }
            """)
            print(f"  [debug] card selector counts: {debug_cards}")

            mutuals = _scrape_from_page(page, founder_name)

        print(f"  [✓] Found {len(mutuals)} mutual connections for {founder_name}")
        return mutuals

    except Exception as e:
        print(f"  [!] Error scraping mutuals for {founder_name}: {e}")
        return []


def _scrape_from_modal(page: Page, founder_name: str) -> list[dict]:
    mutuals = []
    try:
        modal = page.query_selector("div.artdeco-modal__content, div[data-test-modal]")
        if not modal:
            return []

        # Scroll inside modal to load all entries
        for _ in range(3):
            page.evaluate("document.querySelector('div.artdeco-modal__content')?.scrollBy(0, 400)")
            _delay(1, 2)

        cards = modal.query_selector_all("li.reusable-search__result-container, li.mn-connection-card, div.entity-result")
        if not cards:
            # Fallback: grab all anchor tags with /in/ inside modal
            cards = modal.query_selector_all("a[href*='/in/']")
            for card in cards:
                try:
                    href = card.get_attribute("href") or ""
                    url = _clean_linkedin_url(href)
                    name = card.inner_text().strip()
                    if url and name and len(name) < 80:
                        mutuals.append({"name": name, "linkedin_url": url, "mutual_with": founder_name})
                except Exception:
                    continue
            return mutuals

        for card in cards:
            try:
                link = card.query_selector("a[href*='/in/']")
                if not link:
                    continue
                href = link.get_attribute("href") or ""
                url = _clean_linkedin_url(href)
                if not url:
                    continue
                name_el = card.query_selector(
                    "span.entity-result__title-text, span.mn-connection-card__name, "
                    "span[aria-hidden='true'], .actor-name"
                )
                name = name_el.inner_text().strip() if name_el else link.inner_text().strip()
                if name and url:
                    mutuals.append({"name": name, "linkedin_url": url, "mutual_with": founder_name})
            except Exception:
                continue

        # Close modal
        try:
            close_btn = page.query_selector("button[aria-label='Dismiss'], button.artdeco-modal__dismiss")
            if close_btn:
                close_btn.click()
                _delay(1, 2)
        except Exception:
            pass

    except Exception as e:
        print(f"  [!] Modal scrape error: {e}")

    return mutuals


def _scrape_from_page(page: Page, founder_name: str) -> list[dict]:
    mutuals = []
    seen_urls = set()
    try:
        # Scroll to load more results
        for _ in range(3):
            page.evaluate("window.scrollBy(0, 600)")
            _delay(1, 2)

        # Grab all /in/ anchor tags — LinkedIn uses obfuscated class names so we match by href
        links = page.query_selector_all("a[href*='/in/']")
        for link in links:
            try:
                href = link.get_attribute("href") or ""
                url  = _clean_linkedin_url(href)
                if not url or url in seen_urls:
                    continue

                # Get name from inner text of the anchor
                raw_name = link.inner_text().strip()
                # LinkedIn puts "Name\nView Name's profile" — take first line only
                name = raw_name.split("\n")[0].strip()

                # Skip empty names, the founder themselves, and nav/sidebar links
                if not name or len(name) > 60:
                    continue
                if founder_name.lower() in name.lower():
                    continue
                # Skip profile photo links (no text)
                if not name:
                    continue

                seen_urls.add(url)
                mutuals.append({"name": name, "linkedin_url": url, "mutual_with": founder_name})
                print(f"  [+] Mutual found: {name} — {url}")
            except Exception:
                continue
    except Exception as e:
        print(f"  [!] Page scrape error: {e}")

    return mutuals


def _clean_linkedin_url(href: str) -> str:
    match = re.search(r"(https?://(?:www\.)?linkedin\.com/in/[A-Za-z0-9\-_%]+)", href)
    if match:
        return match.group(1)
    # href may be relative like /in/username
    match = re.search(r"/in/([A-Za-z0-9\-_%]+)", href)
    if match:
        return f"https://www.linkedin.com/in/{match.group(1)}"
    return ""
