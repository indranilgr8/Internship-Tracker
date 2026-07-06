"""Central configuration for the internship tracker.

Loads secrets from a .env file (see .env.example) and defines all
non-secret settings: search terms, target companies, and runtime knobs.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Database ---------------------------------------------------------
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "internships.db")

# --- Email / SMTP -------------------------------------------------------
SMTP_SERVER: str = "smtp.gmail.com"
SMTP_PORT: int = 587
GMAIL_ADDRESS: str = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")
RECIPIENT_EMAIL: str = os.getenv("RECIPIENT_EMAIL", GMAIL_ADDRESS)

# --- Digest behavior ------------------------------------------------------
EXPIRING_SOON_DAYS: int = int(os.getenv("EXPIRING_SOON_DAYS", "3"))

# --- Logging ------------------------------------------------------------
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# --- Scraping targets -----------------------------------------------------
TARGET_GRAD_SEASON: str = "Summer 2027"

# Keywords used against general job boards (Indeed, LinkedIn)
SEARCH_KEYWORDS: list[str] = [
    "software engineer intern 2027",
    "computer science intern 2027",
    "software engineering internship summer 2027",
]

# Geography filter passed to job board searches. Empty string == anywhere.
SEARCH_LOCATION: str = os.getenv("SEARCH_LOCATION", "United States")

# GitHub README that Simplify/speedyapply maintains with curated internships.
# Simplify opens a new repo for each recruiting season; if the upcoming
# season's repo doesn't exist yet, github_speedyapply.py falls back to
# GITHUB_SPEEDYAPPLY_FALLBACK_REPO automatically.
GITHUB_SPEEDYAPPLY_REPO: str = "SimplifyJobs/Summer2027-Internships"
GITHUB_SPEEDYAPPLY_FALLBACK_REPO: str = "SimplifyJobs/Summer2026-Internships"

# Direct company career pages to monitor. `type` tells company_careers.py
# which scraping strategy to use for that site.
COMPANY_CAREER_SITES: list[dict] = [
    {
        "name": "Amazon",
        "type": "amazon",
        "url": "https://www.amazon.jobs/en/search.json",
    },
    {
        "name": "Google",
        "type": "google",
        "url": "https://www.google.com/about/careers/applications/jobs/results/",
    },
    {
        "name": "Microsoft",
        "type": "microsoft",
        "url": "https://apply.careers.microsoft.com/api/pcsx/search",
    },
    {
        "name": "Mastercard",
        "type": "workday",
        "workday_tenant": "mastercard",
        "workday_site": "CorporateCareers",
        "url": "https://mastercard.wd1.myworkdayjobs.com/wday/cxs/mastercard/CorporateCareers/jobs",
    },
    {
        # WWT's career site runs on ADP RTI (Angular SPA), not Workday. There
        # is no stable per-job deep link available without a live session,
        # so listings link back to this search results page.
        "name": "WWT",
        "type": "wwt_adp",
        "url": "https://myjobs.adp.com/wwtexternalcareersite/cx/job-listing?keyword=intern",
    },
    {
        # Edward Jones' career site is WordPress (Avada/Fusion builder) with
        # a client-rendered job search, not Workday.
        "name": "Edward Jones",
        "type": "edwardjones",
        "url": "https://careers.edwardjones.com/job-search-results/?location=United+States&country=US&radius=25&units=km",
    },
    {
        "name": "Centene",
        "type": "workday",
        "workday_tenant": "centene",
        "workday_site": "centene_external",
        "url": "https://centene.wd5.myworkdayjobs.com/wday/cxs/centene/centene_external/jobs",
    },
    {
        # Bayer's career site is protected by bot-detection (WAF) that
        # blocks automated browsers outright, including Playwright. This is
        # intentionally NOT bypassed. scrape_bayer() logs a warning and
        # returns [] so it doesn't break the rest of the pipeline.
        "name": "Bayer",
        "type": "bayer",
        "url": "https://career.bayer.com/",
    },
    {
        "name": "Boeing",
        "type": "workday",
        "workday_tenant": "boeing",
        "workday_site": "EXTERNAL_CAREERS",
        "url": "https://boeing.wd1.myworkdayjobs.com/wday/cxs/boeing/EXTERNAL_CAREERS/jobs",
    },
]

# --- HTTP behavior --------------------------------------------------------
REQUEST_TIMEOUT: int = 15
REQUEST_HEADERS: dict = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}
RATE_LIMIT_DELAY_SECONDS: float = 1.5
