import os

LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

# Safety limits
MAX_CONNECTS_PER_DAY = 10
MIN_DELAY = 3      # seconds
MAX_DELAY = 8      # seconds

# Files — always relative to this folder
_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_FILE = os.path.join(_DIR, "cookies.json")
CSV_INPUT = os.path.join(_DIR, "..", "founders.csv")
LOG_FILE = os.path.join(_DIR, "bot_log.json")
