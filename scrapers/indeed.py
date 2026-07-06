"""Scraper for Indeed job search results (CS internship, Summer 2027).

Indeed renders search results with heavy JS and active bot-detection, so
this uses Playwright (headless Chromium) rather than plain requests. Indeed
does not offer a free public search API for this use case.

NOTE: In practice, Indeed serves a CAPTCHA challenge page to headless
browsers fairly often — confirmed while building this scraper. That
challenge is intentionally NOT bypassed here (no CAPTCHA-solving, no
fingerprint spoofing beyond a realistic user agent). When that happens,
`_parse_cards` simply finds no job cards and this returns []; it fails
soft rather than blocking the rest of the pipeline. Treat Indeed as a
best-effort source, not a guaranteed one.

Indeed's Terms of Service restrict automated access. This is intended for
low-frequency, personal-use polling (a few searches, once a day) — keep
delays in place and do not raise scrape frequency or parallelism.
"""

import logging
import urllib.parse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

import config

logger = logging.getLogger(__name__)

SOURCE_NAME = "indeed"
BASE_URL = "https://www.indeed.com/jobs"


def _build_search_url(keyword: str) -> str:
    """Build an Indeed job-search URL for a keyword + configured location."""
    params = {"q": keyword, "l": config.SEARCH_LOCATION, "fromage": "7"}
    return f"{BASE_URL}?{urllib.parse.urlencode(params)}"


def _parse_cards(page) -> list[dict]:
    """Extract listing dicts from job cards on the current results page."""
    listings: list[dict] = []
    cards = page.query_selector_all("div.job_seen_beacon, div.cardOutline")

    for card in cards:
        try:
            title_el = card.query_selector("h2.jobTitle a, a.jcs-JobTitle")
            company_el = card.query_selector('[data-testid="company-name"]')
            location_el = card.query_selector('[data-testid="text-location"]')
            date_el = card.query_selector('[data-testid="myJobsStateDate"], .date')

            if not title_el:
                continue

            title = title_el.inner_text().strip()
            href = title_el.get_attribute("href") or ""
            url = urllib.parse.urljoin("https://www.indeed.com", href)
            company = company_el.inner_text().strip() if company_el else "Unknown"
            location = location_el.inner_text().strip() if location_el else ""
            date_posted = date_el.inner_text().strip() if date_el else ""

            listings.append(
                {
                    "company": company,
                    "title": title,
                    "location": location,
                    "url": url,
                    "date_posted": date_posted,
                    "source": SOURCE_NAME,
                }
            )
        except Exception:
            logger.exception("indeed: failed to parse one job card, skipping it")
            continue

    return listings


def scrape() -> list[dict]:
    """Run an Indeed search for each configured keyword. Returns [] on failure.

    Requires `playwright install chromium` to have been run at least once.
    """
    all_listings: list[dict] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=config.REQUEST_HEADERS["User-Agent"])
            page = context.new_page()

            for keyword in config.SEARCH_KEYWORDS:
                url = _build_search_url(keyword)
                try:
                    page.goto(url, timeout=config.REQUEST_TIMEOUT * 1000)
                    page.wait_for_selector(
                        "div.job_seen_beacon, div.cardOutline",
                        timeout=10_000,
                    )
                    listings = _parse_cards(page)
                    logger.info("indeed: '%s' -> %d listings", keyword, len(listings))
                    all_listings.extend(listings)
                except PlaywrightTimeoutError:
                    logger.warning("indeed: timed out waiting for results for '%s'", keyword)
                except Exception:
                    logger.exception("indeed: search failed for '%s'", keyword)

            browser.close()
    except Exception:
        logger.exception("indeed: failed to launch Playwright/browser")
        return all_listings

    return all_listings


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for item in scrape():
        print(item)
