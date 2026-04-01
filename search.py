import time
import re
import logging
import requests
from config import SERPAPI_KEY, SEARCH_DELAY, MAX_RESULTS_PER_QUERY

logger = logging.getLogger(__name__)

LINKEDIN_PATTERN = re.compile(r"https?://(?:[a-z]{2}\.)?linkedin\.com/in/[A-Za-z0-9\-_%]+")


def _extract_linkedin_url(text: str) -> str | None:
    match = LINKEDIN_PATTERN.search(text)
    if not match:
        return None
    url = re.sub(r"https?://[a-z]{2}\.linkedin\.com", "https://www.linkedin.com", match.group(0))
    return url


def _parse_name_from_title(title: str) -> str | None:
    parts = re.split(r"\s[-|–]\s", title)
    if parts:
        name = parts[0].strip()
        words = name.split()
        if 1 < len(words) <= 4 and all(w.replace("-", "").isalpha() for w in words):
            return name
    return None


def search_founder(company_name: str) -> dict | None:
    query = f"{company_name} founder LinkedIn"
    params = {
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": MAX_RESULTS_PER_QUERY,
        "engine": "google",
    }

    try:
        resp = requests.get("https://www.searchapi.io/api/v1/search", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Search API request failed for '{company_name}': {e}")
        return None
    finally:
        time.sleep(SEARCH_DELAY)

    for result in data.get("organic_results", []):
        link = result.get("link", "")
        snippet = result.get("snippet", "")
        title = result.get("title", "")

        linkedin_url = _extract_linkedin_url(link) or _extract_linkedin_url(snippet)
        if not linkedin_url:
            continue

        founder_name = _parse_name_from_title(title)
        if founder_name:
            logger.info(f"Found founder for '{company_name}': {founder_name}")
            return {"founder_name": founder_name, "linkedin_url": linkedin_url}

    logger.warning(f"No founder found for '{company_name}'")
    return None
