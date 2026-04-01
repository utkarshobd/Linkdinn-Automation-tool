import csv
import os
from config import CSV_FILE

FIELDS = ["company_name", "founder_name", "linkedin_url", "message", "status"]

PB_FILE = "phantombuster_export.csv"
PB_FIELDS = ["linkedInProfile", "message"]


def load_data():
    if not os.path.exists(CSV_FILE):
        return []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_data(records):
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)


def append_record(record):
    exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow({k: record.get(k, "") for k in FIELDS})


def update_status(linkedin_url, new_status):
    records = load_data()
    for r in records:
        if r["linkedin_url"] == linkedin_url:
            r["status"] = new_status
    save_data(records)


def export_phantombuster_csv():
    records = load_data()
    pending = [r for r in records if r["status"] == "pending" and r["linkedin_url"]]
    with open(PB_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PB_FIELDS)
        writer.writeheader()
        for r in pending:
            writer.writerow({"linkedInProfile": r["linkedin_url"], "message": r["message"]})
    return len(pending), PB_FILE
