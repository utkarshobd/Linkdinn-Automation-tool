# LinkedIn Founder Outreach Automation Tool

Automates finding startup founders from a VC portfolio and sending them personalized LinkedIn connection requests.

📹 **[Watch Demo](https://drive.google.com/drive/folders/1tMw4kM6kQjawLaDL7vKRADl6GAxSKBDR?usp=drive_link)**

---

## How It Works — Big Picture

There are two completely separate parts:

```
PART 1 — Pipeline (root folder)
Scrapes marsshot.vc → Searches Google for founder → Generates message → Saves to founders.csv

PART 2 — Bot (linkedin_bot/ folder)
Reads founders.csv → Opens real Chrome → Logs into LinkedIn → Sends connection requests → Sends follow-ups
```

The `founders.csv` file is the bridge. Pipeline writes to it. Bot reads from it.

---

## Project Structure

```
linkdinn automation tool/
│
├── config.py           ← SearchAPI key, target company, scrape settings
├── scraper.py          ← Scrapes company names from marsshot.vc/portfolio
├── search.py           ← Searches Google via SearchAPI to find founder LinkedIn URLs
├── message_gen.py      ← Generates personalized connection messages (random template or GPT)
├── data.py             ← Reads/writes founders.csv
├── pipeline.py         ← Runs scraper → search → message → save (the full finder flow)
├── founders.csv        ← Main data file, auto-created by pipeline
├── requirements.txt    ← Dependencies for the pipeline
│
└── linkedin_bot/
    ├── config.py       ← LinkedIn credentials, daily limit, delay settings
    ├── browser.py      ← Opens Chrome with anti-detection patches
    ├── auth.py         ← Handles LinkedIn login and cookie save/load
    ├── actions.py      ← Clicks Connect, handles More dropdown, types message, sends
    ├── logger.py       ← Tracks how many requests sent today (enforces daily limit)
    ├── bot.py          ← Main runner — ties everything together
    ├── cookies.json    ← Saved login session, auto-created after first login
    ├── bot_log.json    ← Daily send count log, auto-created
    └── requirements.txt ← Dependencies for the bot (just playwright)
```

---

## Prerequisites

- Python 3.10+
- Google Chrome installed
- SearchAPI account (free) → https://searchapi.io
- LinkedIn account (aged 3+ months recommended)

---

## PART 1 — Pipeline Setup

### Step 1 — Install dependencies

```bash
cd "linkdinn automation tool"
pip install -r requirements.txt
```

### Step 2 — Add your SearchAPI key

Open `config.py` and paste your key:

```python
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "paste_your_key_here")
```

Get your free key at: https://searchapi.io → Dashboard → API Key

### Step 3 — Set your target company

Open `config.py` line 6:

```python
TARGET_COMPANY = "Newton School"   # only process this one company
# TARGET_COMPANY = None            # process ALL companies on the page
```

### Step 4 — Run the pipeline

```bash
python pipeline.py
```

### What pipeline.py does step by step

1. `scraper.py` — fetches `https://marsshot.vc/portfolio` using `requests` + `BeautifulSoup`, parses all `notion-collection-card` divs to extract company names. If fewer than 3 companies are found (page may be JS-rendered), it automatically falls back to Selenium headless Chrome.

2. `search.py` — for each company, sends a Google search query `"{company} founder LinkedIn"` to SearchAPI. Parses the organic results, extracts the first LinkedIn `/in/` URL using regex, and parses the founder's name from the result title.

3. `message_gen.py` — generates a personalized connection message. If `OPENAI_API_KEY` is set in environment, it calls GPT-3.5-turbo for a unique message. Otherwise picks randomly from 4 built-in templates and fills in the founder's first name and company name.

4. `data.py` — appends each result as a row in `founders.csv` with status `pending`. Skips companies already in the CSV.

### founders.csv columns

| column | description |
|---|---|
| company_name | Company scraped from marsshot.vc |
| founder_name | Founder name parsed from Google result title |
| linkedin_url | Full LinkedIn profile URL |
| message | Personalized connection message |
| status | Current status (see status flow below) |

---

## PART 2 — Bot Setup

### Step 1 — Install dependencies

```bash
cd linkedin_bot
pip install -r requirements.txt
playwright install chromium
```

### Step 2 — Add your LinkedIn credentials

Open `linkedin_bot/config.py`:

```python
LINKEDIN_EMAIL = "your_email@gmail.com"
LINKEDIN_PASSWORD = "your_password"
```

### Step 3 — Configure limits (optional)

Also in `linkedin_bot/config.py`:

```python
MAX_CONNECTS_PER_DAY = 10   # hard daily cap, never go above 20
MIN_DELAY = 3               # minimum seconds between actions
MAX_DELAY = 8               # maximum seconds between actions
```

### Step 4 — Run the bot

```bash
cd linkedin_bot
python bot.py
```

### What bot.py does step by step

1. `browser.py` — launches a real visible Chrome window using Playwright. Patches `navigator.webdriver` to `undefined` so LinkedIn cannot detect automation.

2. `auth.py` — checks if `cookies.json` exists. If yes, loads the saved session (no login needed). If no, fills in email and password, submits the login form, waits for the feed to load, then saves cookies for next time. If LinkedIn shows a verification challenge, it pauses and waits for you to complete it manually in the browser window.

3. `bot.py → run_connect()` — reads all rows from `founders.csv` where status is `pending`, `no_connect_button`, or `error`. Respects the daily limit from `bot_log.json`. For each profile:
   - Calls `actions.py → send_connection()`
   - Updates status in `founders.csv` based on result
   - Waits 30–60 seconds before the next profile (human-like pacing)

4. `actions.py → send_connection()` — the core connect logic:
   - Opens the LinkedIn profile URL
   - Scrolls slightly to trigger lazy-loaded elements
   - Calls `_find_connect_button()` which:
     - First checks for a "Pending" button → returns `already_pending`
     - Looks for a Connect button with `aria-label` containing "to connect" directly in the profile actions area
     - If not found, clicks the "More actions" button in the profile actions area, then scopes the search to the opened dropdown container (`artdeco-dropdown__content--is-open`) and looks for an `li` with text "Connect" or "Add"
     - If Message button is found → returns `already_connected`
   - Clicks the Connect button or dropdown item
   - Calls `_handle_connect_modal()` which waits for the dialog, then clicks Send (without adding a note — the message is sent as a follow-up after acceptance)

5. `logger.py` — reads/writes `bot_log.json` to track how many requests were sent today. Resets automatically on a new day.

6. `bot.py → run_followup()` — after run_connect finishes, checks all `requested` profiles. For each one, visits the profile and checks if a Message button is visible (meaning they accepted). If accepted, sends the follow-up message from `FOLLOWUP_MESSAGE` template, then updates status to `messaged`.

---

## Status Flow

```
pending
   │
   ▼
requested        ← connection request sent, waiting for acceptance
   │
   ▼
accepted         ← they accepted, follow-up not sent yet
   │
   ▼
messaged         ← follow-up message sent, done

── other statuses ──
already_connected   ← was already connected before bot ran
not_found           ← profile URL returned 404 or redirected to login
no_connect_button   ← no Connect button and no More dropdown found (retried next run)
error               ← unexpected exception (retried next run)
```

---

## Message Generation

Two modes depending on what's configured:

- **No OpenAI key** — picks randomly from 4 built-in templates in `message_gen.py`, fills in `{name}` and `{company}`
- **With OpenAI key** — set `OPENAI_API_KEY` as an environment variable, and it calls GPT-3.5-turbo to write a unique under-300-character message for each founder. Falls back to templates if the API call fails.

---

## Anti-Detection Measures

| Measure | What it does |
|---|---|
| Real visible Chrome | LinkedIn cannot detect headless mode |
| `navigator.webdriver = undefined` | Hides the Playwright automation flag |
| Cookie reuse | Avoids repeated logins that look suspicious |
| Random delays (3–8s) between actions | Mimics human clicking speed |
| 30–60s wait between profiles | Human-like browsing pattern |
| 10 requests/day hard limit | Stays well under LinkedIn's detection threshold |

---

## Adding a New Founder Manually

If you want to add a founder directly without running the pipeline, just add a row to `founders.csv`:

```
company_name,founder_name,linkedin_url,message,status
YourCompany,John Doe,https://www.linkedin.com/in/johndoe,Hi John...,pending
```

Set status to `pending` and the bot will pick it up on the next run.

---

## Quick Start

```bash
# Step 1 — find founders and populate CSV
cd "linkdinn automation tool"
python pipeline.py

# Step 2 — send connection requests
cd linkedin_bot
python bot.py

# Step 3 — next day, run bot again to send follow-ups to accepted connections
python bot.py
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `No pending profiles found` | Check `founders.csv` — status column may not be `pending` |
| `Login failed` | Check email/password in `linkedin_bot/config.py` |
| `Connect button not found` | LinkedIn UI changed — bot retries automatically next run |
| `401 Unauthorized` from SearchAPI | Get a new API key from searchapi.io |
| Bot closes immediately | Make sure you're running from inside `linkedin_bot/` folder |
| LinkedIn asks for verification | Complete it manually in the browser window, then press Enter in terminal |
| Scraper finds 0 companies | marsshot.vc may be JS-rendered — Selenium fallback will kick in automatically |

---

## Safety Rules

- Keep `MAX_CONNECTS_PER_DAY` at 10 or below. Never go above 20.
- Do not run the bot more than once per day.
- Do not use a brand new LinkedIn account — needs to be at least 3 months old.
- Keep the Chrome window visible while the bot runs, do not minimize it.
- Do not send the exact same message to everyone — the templates and GPT mode handle this automatically.
