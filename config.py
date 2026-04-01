import os

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "key")

# Set to a specific company name to only process that one, or None for all
TARGET_COMPANY = "WorkDuck"

SCRAPE_DELAY = 2
SEARCH_DELAY = 3
MAX_RESULTS_PER_QUERY = 3

PORTFOLIO_URL = "https://marsshot.vc/portfolio"

CSV_FILE = "founders.csv"
