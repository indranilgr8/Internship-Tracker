"""Streamlit dashboard for browsing and triaging scraped internship listings.

Run with: streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

# Allow importing config/database from the project root regardless of
# the working directory `streamlit run` was invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

import database

STATUS_OPTIONS = ["new", "applied", "interviewing", "rejected", "closed", "ignored"]

st.set_page_config(page_title="Internship Tracker", layout="wide")
st.title("Internship Tracker Dashboard")


@st.cache_data(ttl=30)
def load_listings() -> pd.DataFrame:
    """Load all listings from SQLite into a DataFrame."""
    rows = database.get_all_listings()
    if not rows:
        return pd.DataFrame(
            columns=[
                "id", "company", "title", "location", "url", "source",
                "date_posted", "deadline", "first_seen", "last_seen", "status",
            ]
        )
    return pd.DataFrame([dict(row) for row in rows])


df = load_listings()

if df.empty:
    st.info("No listings yet. Run `python main.py` to scrape and populate the database.")
    st.stop()

# --- Filters ---------------------------------------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    company_filter = st.multiselect("Company", sorted(df["company"].dropna().unique()))
with col2:
    source_filter = st.multiselect("Source", sorted(df["source"].dropna().unique()))
with col3:
    status_filter = st.multiselect("Status", STATUS_OPTIONS)

filtered = df.copy()
if company_filter:
    filtered = filtered[filtered["company"].isin(company_filter)]
if source_filter:
    filtered = filtered[filtered["source"].isin(source_filter)]
if status_filter:
    filtered = filtered[filtered["status"].isin(status_filter)]

st.caption(f"Showing {len(filtered)} of {len(df)} listings")

# --- Editable table with a status dropdown per row --------------------------
edited = st.data_editor(
    filtered,
    key="listings_editor",
    hide_index=True,
    use_container_width=True,
    disabled=[c for c in filtered.columns if c != "status"],
    column_config={
        "status": st.column_config.SelectboxColumn(
            "Status", options=STATUS_OPTIONS, required=True
        ),
        "url": st.column_config.LinkColumn("URL"),
    },
)

# --- Persist any status changes back to SQLite -----------------------------
if not edited.equals(filtered):
    changed_rows = edited[edited["status"] != filtered["status"]]
    for _, row in changed_rows.iterrows():
        database.update_status(int(row["id"]), row["status"])
    if not changed_rows.empty:
        st.success(f"Updated status for {len(changed_rows)} listing(s).")
        st.cache_data.clear()
        st.rerun()
