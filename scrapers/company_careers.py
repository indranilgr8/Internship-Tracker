"""Scrapers for direct company career pages.

Each employer exposes jobs a different way:

- Amazon:       public `amazon.jobs` search JSON endpoint.
- Microsoft:    public `gcsservices.careers.microsoft.com` search API.
- Google:       careers.google.com's internal search API — this one moves
                around the most; treat it as best-effort and check logs if
                it silently returns 0 results.
- Mastercard, Centene, Boeing: all Workday-hosted, which exposes a
  consistent `wday/cxs/<tenant>/<site>/jobs` JSON POST endpoint. Tenant/site
  slugs were confirmed by inspecting each company's actual career site
  (they don't always match the obvious guess, e.g. Boeing's site is
  "EXTERNAL_CAREERS" on the wd1 pod, not "External" on wd5).
- WWT:          ADP RTI (Angular SPA). The real search API requires a
                short-lived signed token minted client-side, so this uses
                Playwright to render the search results page instead of
                calling the API directly.
- Edward Jones: WordPress (Avada/Fusion builder) with a client-rendered
                job search widget; also scraped via Playwright.
- Bayer:        career site is behind bot-detection (WAF) that blocks
                automated browsers outright. This is intentionally NOT
                bypassed — scrape_bayer() logs a warning and returns [].

Every per-company function fails soft (logs + returns []) so one broken
integration never blocks scraping the rest.
"""

import logging

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

import config

logger = logging.getLogger(__name__)

INTERN_QUERY = "software engineer intern"


def _get_company_config(name: str) -> dict:
    for site in config.COMPANY_CAREER_SITES:
        if site["name"] == name:
            return site
    raise KeyError(f"No COMPANY_CAREER_SITES entry for '{name}'")


def scrape_amazon() -> list[dict]:
    """Query Amazon's public jobs search JSON endpoint for intern roles."""
    site = _get_company_config("Amazon")
    params = {
        "query": INTERN_QUERY,
        "result_limit": 20,
        "sort": "recent",
        "category": "student-programs",
        "country": "USA",
        "offset": 0,
    }
    try:
        response = requests.get(
            site["url"], params=params, headers=config.REQUEST_HEADERS, timeout=config.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        logger.exception("company_careers: Amazon request/parse failed")
        return []

    listings = []
    for job in data.get("jobs", []):
        listings.append(
            {
                "company": "Amazon",
                "title": job.get("title", ""),
                "location": ", ".join(filter(None, [job.get("city"), job.get("state"), job.get("country")])),
                "url": "https://www.amazon.jobs" + job.get("job_path", ""),
                "date_posted": job.get("posted_date", ""),
                "source": "company_careers",
            }
        )
    logger.info("company_careers: Amazon -> %d listings", len(listings))
    return listings


def scrape_microsoft() -> list[dict]:
    """Query Microsoft's public careers search API for intern roles."""
    site = _get_company_config("Microsoft")
    params = {
        "domain": "microsoft.com",
        "query": INTERN_QUERY,
        "location": "",
        "start": 0,
    }
    try:
        response = requests.get(
            site["url"], params=params, headers=config.REQUEST_HEADERS, timeout=config.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        logger.exception("company_careers: Microsoft request/parse failed")
        return []

    listings = []
    for job in data.get("data", {}).get("positions", []):
        listings.append(
            {
                "company": "Microsoft",
                "title": job.get("name", ""),
                "location": ", ".join(job.get("locations", [])),
                "url": "https://apply.careers.microsoft.com" + job.get("positionUrl", ""),
                "date_posted": job.get("postedTs", ""),
                "source": "company_careers",
            }
        )
    logger.info("company_careers: Microsoft -> %d listings", len(listings))
    return listings


def scrape_google() -> list[dict]:
    """Best-effort query against Google's careers search API for intern roles.

    Google's internal API shape changes more often than the others here;
    if this starts returning 0 results, check the request in devtools on
    careers.google.com/jobs/results and update `params`/`url` accordingly.
    """
    site = _get_company_config("Google")
    params = {
        "q": "software engineering intern",
        "employment_type": "INTERN",
        "page": 1,
    }
    try:
        response = requests.get(
            site["url"], params=params, headers=config.REQUEST_HEADERS, timeout=config.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        logger.warning("company_careers: Google search API failed or changed shape; skipping")
        return []

    listings = []
    for job in data.get("jobs", []):
        listings.append(
            {
                "company": "Google",
                "title": job.get("title", ""),
                "location": job.get("location", ""),
                "url": job.get("apply_url", "") or job.get("url", ""),
                "date_posted": job.get("publish_date", ""),
                "source": "company_careers",
            }
        )
    logger.info("company_careers: Google -> %d listings", len(listings))
    return listings


def _scrape_workday(site: dict, search_text: str = "intern", limit: int = 20) -> list[dict]:
    """Generic scraper for any Workday-hosted career site (CXS JSON API)."""
    payload = {"appliedFacets": {}, "limit": limit, "offset": 0, "searchText": search_text}
    headers = {**config.REQUEST_HEADERS, "Content-Type": "application/json"}

    try:
        response = requests.post(
            site["url"], json=payload, headers=headers, timeout=config.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        logger.exception("company_careers: Workday request/parse failed for %s", site["name"])
        return []

    base_url = site["url"].split("/wday/cxs/")[0]
    listings = []
    for job in data.get("jobPostings", []):
        listings.append(
            {
                "company": site["name"],
                "title": job.get("title", ""),
                "location": job.get("locationsText", ""),
                "url": base_url + job.get("externalPath", ""),
                "date_posted": job.get("postedOn", ""),
                "source": "company_careers",
            }
        )
    logger.info("company_careers: %s -> %d listings", site["name"], len(listings))
    return listings


def scrape_wwt() -> list[dict]:
    """Render WWT's ADP-hosted job search results with Playwright.

    There is no stable per-job deep link available without a live SPA
    session, so every listing's `url` points back to this search page
    rather than an individual job.
    """
    site = _get_company_config("WWT")
    listings: list[dict] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=config.REQUEST_HEADERS["User-Agent"])
            page.goto(site["url"], timeout=config.REQUEST_TIMEOUT * 1000, wait_until="networkidle")
            page.wait_for_timeout(2000)

            cards = page.query_selector_all(".job-details")
            for card in cards:
                title_el = card.query_selector("h3 sdf-button, h3")
                location_el = card.query_selector(".reqLocation")
                if not title_el:
                    continue
                title = (title_el.get_attribute("aria-label") or title_el.inner_text()).strip()
                location = location_el.inner_text().strip() if location_el else ""
                listings.append(
                    {
                        "company": "WWT",
                        "title": title,
                        "location": location,
                        "url": site["url"],
                        "date_posted": "",
                        "source": "company_careers",
                    }
                )
            browser.close()
    except PlaywrightTimeoutError:
        logger.warning("company_careers: WWT page timed out")
    except Exception:
        logger.exception("company_careers: WWT scrape failed")

    logger.info("company_careers: WWT -> %d listings", len(listings))
    return listings


def scrape_edwardjones() -> list[dict]:
    """Render Edward Jones' WordPress job search and filter for intern roles.

    The search page doesn't take a reliable keyword query param, so this
    fetches the current results and filters client-side on the title.
    """
    site = _get_company_config("Edward Jones")
    listings: list[dict] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=config.REQUEST_HEADERS["User-Agent"])
            page.goto(site["url"], timeout=config.REQUEST_TIMEOUT * 1000, wait_until="networkidle")
            page.wait_for_timeout(1500)
            html = page.content()
            browser.close()
    except PlaywrightTimeoutError:
        logger.warning("company_careers: Edward Jones page timed out")
        return listings
    except Exception:
        logger.exception("company_careers: Edward Jones scrape failed")
        return listings

    soup = BeautifulSoup(html, "lxml")
    for job_div in soup.select("div.job.clearfix"):
        title_el = job_div.select_one(".jobTitle a")
        location_el = job_div.select_one(".location")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if "intern" not in title.lower():
            continue
        href = title_el.get("href", "")
        listings.append(
            {
                "company": "Edward Jones",
                "title": title,
                "location": location_el.get_text(strip=True) if location_el else "",
                "url": "https://careers.edwardjones.com" + href if href.startswith("/") else href,
                "date_posted": "",
                "source": "company_careers",
            }
        )

    logger.info("company_careers: Edward Jones -> %d listings", len(listings))
    return listings


def scrape_bayer() -> list[dict]:
    """Bayer's career site blocks automated browsers via bot-detection (WAF).

    This is intentionally not bypassed. Logs a warning and returns [] so
    the rest of the pipeline is unaffected; check the site manually if you
    need Bayer listings.
    """
    logger.warning(
        "company_careers: Bayer's career site blocks automated access (WAF bot-detection); "
        "skipping. Check https://career.bayer.com/ manually."
    )
    return []


_DISPATCH = {
    "amazon": lambda site: scrape_amazon(),
    "microsoft": lambda site: scrape_microsoft(),
    "google": lambda site: scrape_google(),
    "workday": _scrape_workday,
    "wwt_adp": lambda site: scrape_wwt(),
    "edwardjones": lambda site: scrape_edwardjones(),
    "bayer": lambda site: scrape_bayer(),
}


def scrape() -> list[dict]:
    """Scrape every configured company career site. Returns aggregated listings.

    A failure in one company's scraper is logged and skipped; it never
    prevents the others from running.
    """
    all_listings: list[dict] = []

    for site in config.COMPANY_CAREER_SITES:
        handler = _DISPATCH.get(site["type"])
        if handler is None:
            logger.warning("company_careers: no handler for type '%s' (%s)", site["type"], site["name"])
            continue
        try:
            all_listings.extend(handler(site))
        except Exception:
            logger.exception("company_careers: unhandled failure scraping %s", site["name"])

    return all_listings


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for item in scrape():
        print(item)
