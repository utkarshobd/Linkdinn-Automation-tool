import json
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from datetime import date
from config import LOG_FILE, MAX_CONNECTS_PER_DAY


def _load_log() -> dict:
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"date": str(date.today()), "count": 0, "sent": []}


def _save_log(log: dict):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)


def get_today_count() -> int:
    log = _load_log()
    if log["date"] != str(date.today()):
        return 0
    return log["count"]


def can_send_today() -> bool:
    return get_today_count() < MAX_CONNECTS_PER_DAY


def record_sent(linkedin_url: str, founder_name: str):
    log = _load_log()
    if log["date"] != str(date.today()):
        log = {"date": str(date.today()), "count": 0, "sent": []}
    log["count"] += 1
    log["sent"].append({"url": linkedin_url, "name": founder_name})
    _save_log(log)
    print(f"  [log] {log['count']}/{MAX_CONNECTS_PER_DAY} sent today")
