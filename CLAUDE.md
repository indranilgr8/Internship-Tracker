# Internship Tracker — Claude Code Project Memory

## Project Purpose
Automated daily CS internship monitoring system for Ishaan Sengupta (Missouri S&T, Class of 2029). Searches LinkedIn, Indeed, GitHub speedyapply, Handshake, ZipRecruiter, Wellfound, and direct company career pages every morning at 7 AM CST. Sends an HTML email digest of new and expiring listings.

## Tech Stack
- Python 3.11
- SQLite (via sqlite3 stdlib)
- requests + BeautifulSoup4 for scraping
- Playwright for JS-heavy pages
- Gmail SMTP (smtplib) for email
- Streamlit for dashboard
- GitHub Actions for scheduling

## File Structure
See system design document. Key files:
- main.py: orchestrator
- config.py: all settings
- database.py: SQLite CRUD
- emailer.py: digest builder + sender
- scrapers/: one file per job source
- .github/workflows/daily_run.yml: cron schedule

## Coding Conventions
- Type hints on all functions
- Docstrings on all functions
- Error handling with try/except + logging
- Never hardcode credentials — use .env
- All secrets in GitHub Actions Secrets

## Commands
- Run tracker: python main.py
- Run dashboard: streamlit run dashboard/app.py
- Install deps: pip install -r requirements.txt
- Install Playwright browsers: playwright install chromium