"""Orchestrator: run every scraper, persist results, and email a digest.

Run manually with `python main.py`, or on a schedule via
.github/workflows/daily_run.yml (daily at 7 AM CST).
"""

import logging

import config
import database
import emailer
from scrapers import company_careers, github_speedyapply, indeed, linkedin

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

SCRAPERS = [
    ("github_speedyapply", github_speedyapply.scrape),
    ("indeed", indeed.scrape),
    ("linkedin", linkedin.scrape),
    ("company_careers", company_careers.scrape),
]


def run_scrapers() -> tuple[int, int]:
    """Run every scraper and store results, tolerating individual failures.

    Returns:
        (total_seen, total_new) counts across all scrapers.
    """
    total_seen = 0
    total_new = 0

    for name, scrape_fn in SCRAPERS:
        try:
            listings = scrape_fn()
        except Exception:
            logger.exception("main: scraper '%s' crashed, skipping", name)
            continue

        for listing in listings:
            total_seen += 1
            if database.insert_if_new(listing):
                total_new += 1

        logger.info("main: '%s' contributed %d listings", name, len(listings))

    return total_seen, total_new


def main() -> None:
    """Entry point: init db, scrape everything, email the digest."""
    logger.info("=== Internship tracker run starting ===")
    database.init_db()

    total_seen, total_new = run_scrapers()
    logger.info("main: scraped %d listings total, %d new", total_seen, total_new)

    new_today = database.get_new_today()
    expiring_soon = database.get_expiring_soon()
    logger.info(
        "main: digest will include %d new-today and %d expiring-soon listings",
        len(new_today),
        len(expiring_soon),
    )

    html = emailer.build_digest_html(new_today, expiring_soon)
    sent = emailer.send_digest(html)
    if not sent:
        logger.warning("main: digest email was not sent (see prior errors)")

    logger.info("=== Internship tracker run complete ===")


if __name__ == "__main__":
    main()
