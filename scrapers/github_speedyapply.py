"""Scraper for the SimplifyJobs Summer-Internships README.

The repo maintains its listings as raw HTML `<table>` blocks embedded in
the markdown README (one table per category: Software Engineering, Data
Science/AI/ML, Hardware Engineering, Product Management, Quant Finance).
This is far more reliable to parse than any job board's HTML: no JS, no
anti-bot measures, just a file served straight from GitHub.

Row format per table:
    <tr>
      <td><strong><a href="...">Company</a></strong></td>
      <td>Role text</td>
      <td>Location, or <details><summary>N locations</summary>a<br>b</details></td>
      <td><div align="center"><a href="APPLY_URL"><img ...></a> ...</div></td>
      <td>Age, e.g. "2d"</td>
    </tr>

A company cell containing only "↳" means "same company as the row above"
(Simplify's way of grouping multiple openings/locations under one company).
"""

import logging

import requests
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)

SOURCE_NAME = "github_speedyapply"


def _readme_url(repo: str) -> str:
    return f"https://raw.githubusercontent.com/{repo}/dev/README.md"


def fetch_readme() -> str:
    """Download the raw README markdown (with embedded HTML tables) for the tracked repo.

    Simplify opens a new repo each recruiting season. If the configured
    season's repo doesn't exist yet (404), falls back to the prior
    season's repo so the scraper keeps working until the new one is live.
    """
    response = requests.get(
        _readme_url(config.GITHUB_SPEEDYAPPLY_REPO),
        headers=config.REQUEST_HEADERS,
        timeout=config.REQUEST_TIMEOUT,
    )
    if response.status_code == 404:
        logger.warning(
            "github_speedyapply: %s not found yet, falling back to %s",
            config.GITHUB_SPEEDYAPPLY_REPO,
            config.GITHUB_SPEEDYAPPLY_FALLBACK_REPO,
        )
        response = requests.get(
            _readme_url(config.GITHUB_SPEEDYAPPLY_FALLBACK_REPO),
            headers=config.REQUEST_HEADERS,
            timeout=config.REQUEST_TIMEOUT,
        )
    response.raise_for_status()
    return response.text


def _row_cells(row) -> list:
    return row.find_all("td", recursive=False)


def parse_readme(markdown: str) -> list[dict]:
    """Parse every listings table out of the README.

    Returns:
        List of listing dicts with keys company, title, location, url,
        date_posted, source.
    """
    soup = BeautifulSoup(markdown, "lxml")
    listings: list[dict] = []
    last_company = ""

    for table in soup.find_all("table"):
        body = table.find("tbody") or table
        for row in body.find_all("tr"):
            cells = _row_cells(row)
            if len(cells) < 4:
                continue

            company_cell, role_cell, location_cell = cells[0], cells[1], cells[2]
            link_cell = cells[3]
            date_cell = cells[4].get_text(strip=True) if len(cells) > 4 else ""

            company_text = company_cell.get_text(strip=True)
            is_continuation = company_text in ("↳", "")
            company = last_company if is_continuation else company_text
            if not is_continuation:
                last_company = company

            title = role_cell.get_text(strip=True)
            details = location_cell.find("details")
            if details:
                summary = details.find("summary")
                if summary:
                    summary.extract()
                location = details.get_text(separator=", ", strip=True)
            else:
                location = location_cell.get_text(separator=", ", strip=True)

            apply_link = link_cell.find("a", href=True)
            url = apply_link["href"] if apply_link else ""

            if not company or not title:
                continue

            listings.append(
                {
                    "company": company,
                    "title": title,
                    "location": location,
                    "url": url,
                    "date_posted": date_cell,
                    "source": SOURCE_NAME,
                }
            )

    return listings


def scrape() -> list[dict]:
    """Fetch and parse the speedyapply README. Returns [] on any failure."""
    try:
        markdown = fetch_readme()
        listings = parse_readme(markdown)
        logger.info("github_speedyapply: parsed %d listings", len(listings))
        return listings
    except requests.RequestException:
        logger.exception("github_speedyapply: failed to fetch README")
        return []
    except Exception:
        logger.exception("github_speedyapply: failed to parse README")
        return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for item in scrape():
        print(item)
