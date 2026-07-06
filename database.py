"""SQLite persistence layer for scraped internship listings.

Schema
------
listings(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    hash        TEXT UNIQUE NOT NULL,   -- dedup key: sha256(company|title|url)
    company     TEXT NOT NULL,
    title       TEXT NOT NULL,
    location    TEXT,
    url         TEXT,
    source      TEXT,                   -- e.g. "github_speedyapply", "indeed"
    date_posted TEXT,                   -- free-text as scraped ("2d ago", "2026-07-01", ...)
    deadline    TEXT,                   -- ISO date (YYYY-MM-DD) if known, else NULL
    first_seen  TEXT NOT NULL,          -- ISO datetime, set on insert
    last_seen   TEXT NOT NULL,          -- ISO datetime, bumped every time it's re-scraped
    status      TEXT NOT NULL DEFAULT 'new'  -- new/applied/interviewing/rejected/closed/ignored
)
"""

import hashlib
import logging
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Iterator, Optional

import config

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    hash        TEXT UNIQUE NOT NULL,
    company     TEXT NOT NULL,
    title       TEXT NOT NULL,
    location    TEXT,
    url         TEXT,
    source      TEXT,
    date_posted TEXT,
    deadline    TEXT,
    first_seen  TEXT NOT NULL,
    last_seen   TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'new'
);
"""


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection with row access by column name."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the listings table if it does not already exist."""
    try:
        with _connect() as conn:
            conn.execute(_SCHEMA)
        logger.info("Database initialized at %s", config.DATABASE_PATH)
    except sqlite3.Error:
        logger.exception("Failed to initialize database")
        raise


def make_hash(company: str, title: str, url: str) -> str:
    """Build a stable dedup key for a listing.

    Uses company + title + url rather than url alone since some sources
    reuse the same application link across multiple postings.
    """
    raw = f"{company.strip().lower()}|{title.strip().lower()}|{url.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def insert_if_new(listing: dict) -> bool:
    """Insert a listing if unseen, otherwise refresh its last_seen timestamp.

    Args:
        listing: dict with keys company, title, url, source, and optionally
            location, date_posted, deadline.

    Returns:
        True if this was a brand-new listing, False if it already existed.
    """
    company = listing["company"]
    title = listing["title"]
    url = listing.get("url", "")
    listing_hash = make_hash(company, title, url)
    now = datetime.now().isoformat(timespec="seconds")

    try:
        with _connect() as conn:
            existing = conn.execute(
                "SELECT id FROM listings WHERE hash = ?", (listing_hash,)
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE listings SET last_seen = ? WHERE hash = ?",
                    (now, listing_hash),
                )
                return False

            conn.execute(
                """
                INSERT INTO listings (
                    hash, company, title, location, url, source,
                    date_posted, deadline, first_seen, last_seen, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')
                """,
                (
                    listing_hash,
                    company,
                    title,
                    listing.get("location"),
                    url,
                    listing.get("source"),
                    listing.get("date_posted"),
                    listing.get("deadline"),
                    now,
                    now,
                ),
            )
            logger.info("New listing: %s - %s", company, title)
            return True
    except sqlite3.Error:
        logger.exception("Failed to insert listing %s - %s", company, title)
        return False


def get_new_today() -> list[sqlite3.Row]:
    """Return listings whose first_seen date is today (local time)."""
    today = date.today().isoformat()
    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT * FROM listings WHERE date(first_seen) = ? ORDER BY company, title",
                (today,),
            ).fetchall()
        return rows
    except sqlite3.Error:
        logger.exception("Failed to fetch new-today listings")
        return []


def get_expiring_soon(days: Optional[int] = None) -> list[sqlite3.Row]:
    """Return non-closed listings with a known deadline within `days` days.

    Listings without a `deadline` value are skipped since expiry can't be
    determined for them.
    """
    days = days if days is not None else config.EXPIRING_SOON_DAYS
    today = date.today()
    cutoff = today + timedelta(days=days)
    try:
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM listings
                WHERE deadline IS NOT NULL
                  AND deadline != ''
                  AND date(deadline) BETWEEN date(?) AND date(?)
                  AND status NOT IN ('closed', 'rejected', 'ignored')
                ORDER BY deadline
                """,
                (today.isoformat(), cutoff.isoformat()),
            ).fetchall()
        return rows
    except sqlite3.Error:
        logger.exception("Failed to fetch expiring-soon listings")
        return []


def get_all_listings() -> list[sqlite3.Row]:
    """Return every listing, most recently seen first. Used by the dashboard."""
    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT * FROM listings ORDER BY last_seen DESC"
            ).fetchall()
        return rows
    except sqlite3.Error:
        logger.exception("Failed to fetch all listings")
        return []


def update_status(listing_id: int, new_status: str) -> bool:
    """Update the status of a single listing by id.

    Args:
        listing_id: primary key of the listing.
        new_status: one of new/applied/interviewing/rejected/closed/ignored.

    Returns:
        True if a row was updated, False otherwise.
    """
    try:
        with _connect() as conn:
            cursor = conn.execute(
                "UPDATE listings SET status = ? WHERE id = ?",
                (new_status, listing_id),
            )
        return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Failed to update status for listing %s", listing_id)
        return False
