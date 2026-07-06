"""Builds and sends the daily HTML digest email via Gmail SMTP."""

import logging
import smtplib
import sqlite3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date

import config

logger = logging.getLogger(__name__)


def _row_to_html(row: sqlite3.Row) -> str:
    """Render a single listing row as an HTML table row."""
    company = row["company"] or ""
    title = row["title"] or ""
    location = row["location"] or "N/A"
    url = row["url"] or "#"
    source = row["source"] or ""
    deadline = row["deadline"] or "-"
    return f"""
    <tr>
        <td style="padding:8px;border-bottom:1px solid #eee;">{company}</td>
        <td style="padding:8px;border-bottom:1px solid #eee;">
            <a href="{url}" style="color:#1a73e8;text-decoration:none;">{title}</a>
        </td>
        <td style="padding:8px;border-bottom:1px solid #eee;">{location}</td>
        <td style="padding:8px;border-bottom:1px solid #eee;">{deadline}</td>
        <td style="padding:8px;border-bottom:1px solid #eee;font-size:12px;color:#888;">{source}</td>
    </tr>
    """


def _section_table(rows: list[sqlite3.Row]) -> str:
    """Render a list of listing rows as an HTML table, or a placeholder if empty."""
    if not rows:
        return "<p style='color:#888;'>None.</p>"
    body_rows = "".join(_row_to_html(r) for r in rows)
    return f"""
    <table style="width:100%;border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px;">
        <thead>
            <tr style="background:#f5f5f5;text-align:left;">
                <th style="padding:8px;">Company</th>
                <th style="padding:8px;">Title</th>
                <th style="padding:8px;">Location</th>
                <th style="padding:8px;">Deadline</th>
                <th style="padding:8px;">Source</th>
            </tr>
        </thead>
        <tbody>{body_rows}</tbody>
    </table>
    """


def build_digest_html(new_listings: list[sqlite3.Row], expiring_listings: list[sqlite3.Row]) -> str:
    """Build the full HTML body for the daily digest email.

    Args:
        new_listings: rows returned by database.get_new_today().
        expiring_listings: rows returned by database.get_expiring_soon().

    Returns:
        A complete HTML document string.
    """
    today_str = date.today().strftime("%B %d, %Y")
    return f"""
    <html>
    <body style="font-family:Arial,sans-serif;color:#222;max-width:800px;margin:0 auto;">
        <h2>Internship Digest — {today_str}</h2>

        <h3>🆕 New Listings ({len(new_listings)})</h3>
        {_section_table(new_listings)}

        <h3>⏰ Expiring Soon ({len(expiring_listings)})</h3>
        {_section_table(expiring_listings)}

        <p style="color:#aaa;font-size:12px;margin-top:24px;">
            Automated message from the internship tracker.
        </p>
    </body>
    </html>
    """


def send_digest(html: str, subject: str | None = None) -> bool:
    """Send the digest HTML over Gmail SMTP (STARTTLS on port 587).

    Args:
        html: full HTML document, e.g. from build_digest_html().
        subject: optional override for the email subject line.

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    if not config.GMAIL_ADDRESS or not config.GMAIL_APP_PASSWORD:
        logger.error("GMAIL_ADDRESS / GMAIL_APP_PASSWORD not configured; skipping send")
        return False

    subject = subject or f"Internship Digest — {date.today().strftime('%b %d, %Y')}"

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = config.GMAIL_ADDRESS
    message["To"] = config.RECIPIENT_EMAIL
    message.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT, timeout=config.REQUEST_TIMEOUT) as server:
            server.starttls()
            server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
            server.sendmail(config.GMAIL_ADDRESS, config.RECIPIENT_EMAIL, message.as_string())
        logger.info("Digest email sent to %s", config.RECIPIENT_EMAIL)
        return True
    except smtplib.SMTPException:
        logger.exception("Failed to send digest email")
        return False
