import logging
from scraper import get_companies
from search import search_founder
from message_gen import generate_message
from data import load_data, append_record, export_phantombuster_csv
from config import TARGET_COMPANY

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def already_processed(company_name: str, existing: list[dict]) -> bool:
    return any(
        r["company_name"].lower() == company_name.lower() and r["linkedin_url"]
        for r in existing
    )


def run_pipeline():
    logger.info("Step 1: Scraping portfolio companies...")
    companies = get_companies()
    logger.info(f"Found {len(companies)} companies")

    if TARGET_COMPANY:
        companies = [c for c in companies if c.lower() == TARGET_COMPANY.lower()]
        if not companies:
            logger.error(f"'{TARGET_COMPANY}' not found in scraped list.")
            return
        logger.info(f"Targeting only: {companies}")

    existing = load_data()
    new_count = 0

    for company in companies:
        if already_processed(company, existing):
            logger.info(f"Skipping '{company}' (already in CSV)")
            continue

        logger.info(f"Searching founder for: {company}")
        result = search_founder(company)

        if not result:
            append_record({
                "company_name": company,
                "founder_name": "",
                "linkedin_url": "",
                "message": "",
                "status": "not_found",
            })
            continue

        message = generate_message(result["founder_name"], company)
        record = {
            "company_name": company,
            "founder_name": result["founder_name"],
            "linkedin_url": result["linkedin_url"],
            "message": message,
            "status": "pending",
        }
        append_record(record)
        existing.append(record)
        new_count += 1
        logger.info(f"  ✓ {result['founder_name']} — {result['linkedin_url']}")

    logger.info(f"\nPipeline complete. {new_count} new records added.")
    count, path = export_phantombuster_csv()
    logger.info(f"PhantomBuster export: {count} pending profiles → '{path}'")


if __name__ == "__main__":
    run_pipeline()
