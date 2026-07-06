I'm building an automated internship tracker in Python. 
Read my CLAUDE.md for full context. 

Build all files in this exact order:
1. requirements.txt with all dependencies
2. .gitignore (ignore venv/, .env, __pycache__, *.db)
3. .env.example (template with placeholder values)
4. config.py (all settings as described in CLAUDE.md)
5. database.py (SQLite schema + CRUD: init_db, 
   make_hash, insert_if_new, get_new_today, 
   get_expiring_soon, update_status)
6. emailer.py (HTML digest builder + Gmail SMTP sender)
7. scrapers/__init__.py (empty)
8. scrapers/github_speedyapply.py 
   (parse github.com/SimplifyJobs/Summer2027-Internships)
9. scrapers/indeed.py (search Indeed for CS intern 2027)
10. scrapers/linkedin.py (search LinkedIn Jobs)
11. scrapers/company_careers.py (scrape Amazon, Google,
    Microsoft, Mastercard, WWT, Edward Jones, Centene, 
    Bayer, Boeing career pages)
12. main.py (orchestrator: run all scrapers, call send_digest)
13. dashboard/app.py (Streamlit: show all listings, 
    update status dropdown per row)
14. .github/workflows/daily_run.yml 
    (cron: 0 13 * * * = 7 AM CST)

After building all files, run: python main.py