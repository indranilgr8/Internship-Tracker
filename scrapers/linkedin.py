"""Scraper for LinkedIn Jobs search results.

LinkedIn has no free public job-search API. This uses LinkedIn's public
"guest" job search endpoint (the same one that powers infinite-scroll on
linkedin.com/jobs/search for logged-out visitors) since it returns plain
HTML job cards without needing a JS-rendered browser or a logged-in
session/cookies.

NOTE: LinkedIn's ToS restricts automated scraping and this endpoint's
shape can change without notice. Keep this to low-frequency personal use
(one run/day) and do not attempt to log in or bypass authentication.
"""

import logging
import urllib.parse

import requests
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)

SOURCE_NAME = "linkedin"
GUEST_SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"


def _build_params(keyword: str, start: int = 0) -> dict:
    return {
        "keywords": keyword,
        "location": config.SEARCH_LOCATION,
        "f_TPR": "r604800",  # past week
        "start": start,
    }


def _parse_cards(html: str) -> list[dict]:
    """Extract listing dicts from a page of guest-search-endpoint HTML."""
    soup = BeautifulSoup(html, "lxml")
    listings: list[dict] = []

    for card in soup.select("li"):
        try:
            title_el = card.select_one(".base-search-card__title")
            company_el = card.select_one(".base-search-card__subtitle")
            location_el = card.select_one(".job-search-card__location")
            link_el = card.select_one("a.base-card__full-link")
            date_el = card.select_one("time")

            if not title_el or not link_el:
                continue

            listings.append(
                {
                    "company": company_el.get_text(strip=True) if company_el else "Unknown",
                    "title": title_el.get_text(strip=True),
                    "location": location_el.get_text(strip=True) if location_el else "",
                    "url": link_el.get("href", "").split("?")[0],
                    "date_posted": date_el.get("datetime", "") if date_el else "",
                    "source": SOURCE_NAME,
                }
            )
        except Exception:
            logger.exception("linkedin: failed to parse one job card, skipping it")
            continue

    return listings


def _search_keyword(keyword: str, max_pages: int = 2) -> list[dict]:
    """Page through guest search results for a single keyword."""
    results: list[dict] = []

    for page_num in range(max_pages):
        start = page_num * 25
        params = _build_params(keyword, start=start)
        url = f"{GUEST_SEARCH_URL}?{urllib.parse.urlencode(params)}"

        try:
            response = requests.get(
                url, headers=config.REQUEST_HEADERS, timeout=config.REQUEST_TIMEOUT
            )
            if response.status_code == 429:
                logger.warning("linkedin: rate-limited, stopping pagination for '%s'", keyword)
                break
            response.raise_for_status()
        except requests.RequestException:
            logger.exception("linkedin: request failed for '%s' page %d", keyword, page_num)
            break

        page_listings = _parse_cards(response.text)
        if not page_listings:
            break
        results.extend(page_listings)

    return results


def scrape() -> list[dict]:
    """Search LinkedIn Jobs for each configured keyword. Returns [] on failure."""
    all_listings: list[dict] = []

    for keyword in config.SEARCH_KEYWORDS:
        try:
            listings = _search_keyword(keyword)
            logger.info("linkedin: '%s' -> %d listings", keyword, len(listings))
            all_listings.extend(listings)
        except Exception:
            logger.exception("linkedin: search failed for '%s'", keyword)

    return all_listings


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for item in scrape():
        print(item)
