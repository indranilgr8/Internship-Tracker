# Internship Tracker 🎯

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/Automated-GitHub_Actions-2088FF?style=flat&logo=github-actions&logoColor=white)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?style=flat&logo=sqlite&logoColor=white)
![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![Playwright](https://img.shields.io/badge/Scraping-Playwright-45ba4b?style=flat&logo=playwright&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

> **A fully automated daily CS internship monitoring system — runs every morning at 7 AM CST, scrapes multiple job sources, deduplicates listings, and delivers a formatted HTML email digest.**
>
> Built for tracking Summer 2027 CS internship opportunities for a rising sophomore at Missouri S&T.

---

## How It Works

Every morning at 7:00 AM CST, a GitHub Actions workflow wakes up and runs the Python scraper pipeline:

```
GitHub Actions cron (7 AM CST)
        ↓
main.py orchestrates all scrapers
        ↓
┌──────────────────────────────────────────────────┐
│  github_speedyapply  │  indeed  │  linkedin      │
│  company_careers (Amazon, Google, Microsoft,     │
│  Mastercard, WWT, Edward Jones, Centene, Boeing) │
└──────────────────────────────────────────────────┘
        ↓
database.py deduplicates via SHA-256 hash
(company + role + location)
        ↓
SQLite stores all new listings persistently
        ↓
emailer.py builds HTML + plain text digest
        ↓
Gmail SMTP sends digest to recipient inbox
```

Individual scraper failures are caught and logged without crashing the pipeline — if LinkedIn blocks a request, the other scrapers continue running.

---

## Features

- 🔄 **Fully automated** — runs daily via GitHub Actions cron with zero manual intervention
- 🔍 **Multi-source scraping** — GitHub speedyapply list, Indeed, LinkedIn, and 9 direct company career pages
- 🧹 **Smart deduplication** — SHA-256 hash of company + role + location prevents the same listing from ever appearing twice
- 📧 **HTML email digest** — formatted daily email with new listings and listings expiring within 3 days
- 🛡️ **Fault-tolerant** — each scraper runs independently; one failure never stops the rest
- 🗄️ **Persistent SQLite database** — full history of every listing ever found, committed back to the repo after each run
- 📊 **Streamlit dashboard** — local web UI to view listings and update application status
- ⚙️ **Fully configurable** — all keywords, locations, companies, and behavior controlled via `config.py` and `.env`
- 🇺🇸 **US Citizenship flag** — surfaces citizenship-required roles as a distinct category

---

## Tech Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Language | Python | 3.11+ | Core runtime |
| Scheduler | GitHub Actions | — | Daily cron at 7 AM CST |
| HTTP Scraping | requests + BeautifulSoup4 + lxml | 2.32.3 / 4.12.3 / 5.3.0 | Static page scraping |
| JS Scraping | Playwright | 1.49.1 | JavaScript-heavy career pages |
| Database | SQLite (stdlib) | — | Persistent listing storage |
| Email | smtplib (stdlib) + Gmail SMTP | — | Daily HTML digest |
| Dashboard | Streamlit | 1.39.0 | Local status tracking UI |
| Data | pandas | 2.2.3 | Tabular data for dashboard |
| Config | python-dotenv | 1.0.1 | `.env` file loading |

---

## Job Sources

### General Job Boards
| Source | Scraper | What It Fetches |
|---|---|---|
| **GitHub speedyapply** | `scrapers/github_speedyapply.py` | Parses `SimplifyJobs/Summer2027-Internships` README table. Falls back to `SimplifyJobs/Summer2026-Internships` if the 2027 repo doesn't exist yet. |
| **Indeed** | `scrapers/indeed.py` | Searches "software engineer intern 2027", "computer science intern 2027", "software engineering internship summer 2027" across United States. |
| **LinkedIn** | `scrapers/linkedin.py` | Same keyword set, LinkedIn Jobs search. |

### Direct Company Career Pages
| Company | Scraper Strategy | Notes |
|---|---|---|
| **Amazon** | Custom JSON API (`amazon.jobs/en/search.json`) | Amazon exposes a search JSON endpoint — no JS rendering needed |
| **Google** | Custom scraper | Google Careers results page |
| **Microsoft** | Custom API (`apply.careers.microsoft.com/api/pcsx/search`) | Microsoft's internal search API |
| **Mastercard** | Workday (`mastercard.wd1.myworkdayjobs.com`) | Workday CXS API endpoint |
| **WWT** | ADP RTI scraper (`myjobs.adp.com`) | World Wide Technology uses ADP; links back to search results page |
| **Edward Jones** | Custom scraper | WordPress/Avada site with client-rendered search |
| **Centene** | Workday (`centene.wd5.myworkdayjobs.com`) | Workday CXS API endpoint |
| **Boeing** | Workday (`boeing.wd1.myworkdayjobs.com`) | Workday CXS API endpoint |
| **Bayer** | Graceful skip | Bayer's WAF blocks automated browsers including Playwright; scraper logs a warning and returns `[]` without crashing |

---

## Project Structure

```
Internship-Tracker/
├── .github/
│   └── workflows/
│       └── daily_run.yml          # Cron schedule: 7 AM CST daily (13:00 UTC)
├── dashboard/
│   └── app.py                     # Streamlit dashboard — view listings, update status
├── scrapers/
│   ├── __init__.py
│   ├── company_careers.py         # Orchestrates all direct company page scrapers
│   ├── github_speedyapply.py      # Parses SimplifyJobs Summer 2027 internship list
│   ├── indeed.py                  # Indeed job board scraper
│   └── linkedin.py                # LinkedIn Jobs scraper
├── .env.example                   # Template — copy to .env and fill in credentials
├── .gitignore                     # Excludes venv/, .env, __pycache__/
├── CLAUDE.md                      # Claude Code project memory (AI coding context)
├── Project-Creation.md            # Project design and build notes
├── config.py                      # All settings: emails, keywords, companies, behavior
├── database.py                    # SQLite schema, deduplication, CRUD operations
├── emailer.py                     # HTML + plain text digest builder and Gmail sender
├── internships.db                 # SQLite database (auto-updated by each run)
├── main.py                        # Orchestrator: runs scrapers → stores → emails
└── requirements.txt               # All Python dependencies with pinned versions
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Git
- A Gmail account with 2-Step Verification enabled

### 1. Clone the Repository

```bash
git clone https://github.com/indranilgr8/Internship-Tracker.git
cd Internship-Tracker
```

### 2. Create a Virtual Environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows (Command Prompt)
venv\Scripts\activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Configure Environment Variables

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Gmail address used to SEND the digest
GMAIL_ADDRESS=your_email@gmail.com

# Gmail App Password (NOT your regular password)
# Generate at: https://myaccount.google.com/apppasswords
# Requires 2-Step Verification to be enabled first
GMAIL_APP_PASSWORD=your_16_char_app_password

# Who receives the digest (can be the same as GMAIL_ADDRESS)
RECIPIENT_EMAIL=recipient@example.com

# Optional settings (defaults shown)
DATABASE_PATH=internships.db
LOG_LEVEL=INFO
EXPIRING_SOON_DAYS=3
```

> ⚠️ **Never commit your `.env` file.** It is already listed in `.gitignore`.

### 5. Run Manually

```bash
python main.py
```

Check your inbox. The digest email should arrive within 60 seconds.

### 6. Run the Dashboard (Optional)

```bash
streamlit run dashboard/app.py
```

Opens at `http://localhost:8501` — view all listings and update application status.

---

## Automated Scheduling via GitHub Actions

The workflow at `.github/workflows/daily_run.yml` runs automatically every day at **7:00 AM CST (13:00 UTC)**.

### Setting Up GitHub Actions

**Step 1 — Push to GitHub**
```bash
git remote add origin https://github.com/your-username/Internship-Tracker.git
git push -u origin main
```

**Step 2 — Add Repository Secrets**

Go to your repo → **Settings → Secrets and Variables → Actions → New repository secret**

Add these three secrets (type the names manually — do not paste):

| Secret Name | Value |
|---|---|
| `GMAIL_ADDRESS` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | Your 16-character Gmail App Password |
| `RECIPIENT_EMAIL` | Email address to receive the digest |

**Step 3 — Enable and Test**

Go to **Actions tab → Daily Internship Tracker → Run workflow** to trigger a manual test run. Watch the logs for confirmation.

A successful run ends with:
```
INFO  main: digest email was sent
INFO  === Internship tracker run complete ===
```

### Workflow File

```yaml
name: Daily Internship Tracker

on:
  schedule:
    - cron: "0 13 * * *"   # 7 AM CST = 13:00 UTC
  workflow_dispatch:         # Allows manual trigger

jobs:
  scrape-and-notify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Install Playwright browsers
        run: playwright install chromium

      - name: Run tracker
        env:
          GMAIL_ADDRESS:      ${{ secrets.GMAIL_ADDRESS }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
          RECIPIENT_EMAIL:    ${{ secrets.RECIPIENT_EMAIL }}
        run: python main.py
```

> ⚠️ **Important:** The `env` block in the workflow must use `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, and `RECIPIENT_EMAIL` — these are the exact variable names that `config.py` reads. If different names were set as GitHub Secrets, map them here accordingly.

---

## Configuration Reference

All non-secret settings are controlled in `config.py`:

| Setting | Default | Description |
|---|---|---|
| `TARGET_GRAD_SEASON` | `"Summer 2027"` | The recruiting season being monitored |
| `SEARCH_KEYWORDS` | 3 keyword strings | Sent to Indeed and LinkedIn search |
| `SEARCH_LOCATION` | `"United States"` | Geography filter for job boards |
| `GITHUB_SPEEDYAPPLY_REPO` | `SimplifyJobs/Summer2027-Internships` | Primary GitHub list to parse |
| `GITHUB_SPEEDYAPPLY_FALLBACK_REPO` | `SimplifyJobs/Summer2026-Internships` | Fallback if 2027 repo not yet created |
| `EXPIRING_SOON_DAYS` | `3` | Days until deadline to flag ⚠️ |
| `REQUEST_TIMEOUT` | `15` seconds | HTTP request timeout |
| `RATE_LIMIT_DELAY_SECONDS` | `1.5` seconds | Delay between requests to avoid blocks |
| `COMPANY_CAREER_SITES` | 9 companies | List of direct career pages to monitor |

---

## Database Schema

All listings are stored in `internships.db` (SQLite). Key fields:

| Field | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `hash` | TEXT UNIQUE | SHA-256 of company + role + location — deduplication key |
| `company` | TEXT | Company name |
| `role_title` | TEXT | Exact job title as posted |
| `location` | TEXT | City/State, Remote, or Hybrid |
| `deadline` | TEXT | Application deadline or "Rolling" |
| `apply_url` | TEXT | Direct application link |
| `date_found` | TEXT | ISO date when first detected |
| `status` | TEXT | Not Applied / Applied / OA Received / Interview / Offer / Rejected |
| `source` | TEXT | Which scraper found it |
| `active` | INTEGER | 1 = still open, 0 = no longer appearing |

---

## Cost

| Component | Cost |
|---|---|
| GitHub Actions (2,000 min/month free for private repos) | **$0** |
| SQLite database | **$0** |
| Gmail SMTP | **$0** |
| Python libraries | **$0** |
| Playwright (open source) | **$0** |
| **Total** | **$0/month** |

Each daily run takes approximately 2–4 minutes. At 30 runs/month that is ~90–120 minutes, well within the 2,000 free minute limit.

---

## Troubleshooting

**Email not received after a successful run**
- Check spam/junk folder and mark as Not Spam
- Verify the `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` / `RECIPIENT_EMAIL` secrets are set correctly in GitHub Actions
- Confirm the workflow `env` block uses `GMAIL_ADDRESS` (not `EMAIL_SENDER`) to match `config.py`

**Run succeeds but logs show "digest email was not sent"**
- This means `GMAIL_ADDRESS` or `GMAIL_APP_PASSWORD` came through as empty strings
- Check the secret names match exactly what `config.py` expects
- Re-generate the Gmail App Password at myaccount.google.com/apppasswords

**Bayer returns no results**
- Expected. Bayer's WAF actively blocks automated browsers including Playwright. The scraper gracefully returns `[]` and logs a warning. This is by design.

**LinkedIn or Indeed returns no results**
- Both platforms rate-limit and occasionally block GitHub Actions IP ranges. This is normal. The other scrapers (speedyapply, company career pages) will still run and send a digest.

**`playwright install` fails in GitHub Actions**
- Add this step explicitly: `playwright install --with-deps chromium`

---

## What I Built & Learned

This project was built to solve a real problem: tracking dozens of simultaneous internship applications during a competitive recruiting cycle.

**Technical skills demonstrated:**

- Built a **multi-source web scraping pipeline** in Python using requests + BeautifulSoup for static pages and Playwright for JavaScript-rendered career pages
- Implemented **per-site scraping strategies** — Workday's CXS JSON API for Mastercard/Centene/Boeing, Amazon's search JSON endpoint, custom scrapers for ADP RTI (WWT) and WordPress (Edward Jones)
- Designed a **fault-tolerant orchestrator** (`main.py`) where individual scraper failures are caught, logged, and bypassed without crashing the pipeline
- Built **SHA-256 deduplication** at the database layer — the same listing from two different sources never appears twice
- Implemented **Gmail SMTP email delivery** with both HTML and plain text fallback in a single multipart message
- Set up **GitHub Actions cron scheduling** (UTC offset math for CST) with GitHub Secrets for credential management
- Designed a clean **SQLite schema** with an application status state machine (Not Applied → Applied → OA Received → Interview → Offer / Rejected)
- Built a **Streamlit dashboard** for local status tracking and listing management

---

## Future Enhancements

- [ ] ZipRecruiter and Wellfound (AngelList) scrapers
- [ ] Citizenship/clearance-required role flagging (🇺🇸 badge in digest)
- [ ] Weekly Sunday summary email (total found, applied, in-progress, offers)
- [ ] SMS fallback via Twilio when email fails
- [ ] Proxy rotation to reduce LinkedIn/Indeed blocking
- [ ] Automatic `.gitignore` entry for `internships.db` to keep binary out of repo history

---

## Author

**Indranil Sengupta** — built for **Ishaan Sengupta**
Missouri University of Science and Technology — B.S. Computer Science, Class of 2029

[![GitHub](https://img.shields.io/badge/Ishaan's_GitHub-Ishaan3030-181717?style=flat&logo=github)](https://github.com/Ishaan3030)

---

## License

This project is licensed under the [MIT License](LICENSE).
