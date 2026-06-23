import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
from tabulate import tabulate

st.set_page_config(page_title="Screener Viewer", layout="wide")

# ---------------- Sidebar ----------------
st.sidebar.header("🔍 Filters")

# ---------------- TABLE SELECT ----------------
table_choice = st.sidebar.selectbox(
    "Select Table",
    ["company_results", "digit_switch", "initial_switch"]
)

# ---------------- 1) MARKET CAP ----------------
with st.sidebar.expander("By Market Cap", expanded=True):
    mcap_filter = st.radio(
        "Select Market Cap Range",
        ["All", "0 - 50 Cr", "50 - 500 Cr", "500 - 5,000 Cr", "> 5,000 Cr"],
        index=0
    )
    st.markdown("**OR set custom range**")
    col1, col2 = st.columns(2)
    with col1:
        custom_min_mcap = st.number_input("Min (Cr)", value=0, min_value=0, step=50)
    with col2:
        custom_max_mcap = st.number_input("Max (Cr)", value=0, min_value=0, step=50)

# ---------------- 2) SORTING ----------------
with st.sidebar.expander("By Sorting", expanded=False):
    sort_choice = st.radio(
        "Sort Results By:",
        ["None", "Quarterly Difference (diff_qtr)"],
        index=0
    )

# ---------------- 3) DATE POSTED ----------------
with st.sidebar.expander("Date Posted", expanded=False):
    from_date = st.date_input("From Date", value=date(2025, 1, 1))
    to_date = st.date_input("To Date", value=date.today())

# ---------------- Main ----------------
st.title("📊 Screener Digit & Initial Switch Viewer")

# Connect DB
conn = sqlite3.connect("screener_data.db")
df = pd.read_sql_query(f"SELECT * FROM {table_choice}", conn)

# Standardize date column
if 'scrapped_date' in df.columns:
    df['result_posted_date'] = pd.to_datetime(df['scrapped_date'], errors='coerce').dt.date
elif 'scraped_date' in df.columns:
    df['result_posted_date'] = pd.to_datetime(df['scraped_date'], errors='coerce').dt.date
elif 'result_posted_date' in df.columns:
    df['result_posted_date'] = pd.to_datetime(df['result_posted_date'], errors='coerce').dt.date
else:
    st.warning("No date column found in table!")

# Clickable company column
if 'company' in df.columns:
    if 'company_link' in df.columns:
        df['Company'] = df.apply(
            lambda row: f"[{row['company']}](https://www.screener.in{row['company_link']})"
            if pd.notnull(row['company_link']) else row['company'],
            axis=1
        )
    else:
        df['Company'] = df['company']

# ---------------- MARKET CAP FILTER ----------------
if 'market_cap' not in df.columns and 'mcap' in df.columns:
    df.rename(columns={'mcap': 'market_cap'}, inplace=True)

if 'market_cap' in df.columns:
    if custom_min_mcap > 0 or custom_max_mcap > 0:
        # custom range overrides
        if custom_max_mcap > 0:
            df = df[(df['market_cap'] >= custom_min_mcap) & (df['market_cap'] <= custom_max_mcap)]
        else:
            df = df[df['market_cap'] >= custom_min_mcap]
    else:
        # preset ranges
        if mcap_filter == "0 - 50 Cr":
            df = df[(df['market_cap'] >= 0) & (df['market_cap'] <= 50)]
        elif mcap_filter == "50 - 500 Cr":
            df = df[(df['market_cap'] >= 50) & (df['market_cap'] <= 500)]
        elif mcap_filter == "500 - 5,000 Cr":
            df = df[(df['market_cap'] >= 500) & (df['market_cap'] <= 5000)]
        elif mcap_filter == "> 5,000 Cr":
            df = df[df['market_cap'] >= 5000]
        # "All" = no filter

# ---------------- DATE FILTER ----------------
if 'result_posted_date' in df.columns:
    df = df[(df['result_posted_date'] >= from_date) & (df['result_posted_date'] <= to_date)]

# Remove raw columns
for col in ['company', 'company_link']:
    if col in df.columns:
        df.drop(columns=col, inplace=True)

# --- Reorder columns: make 'Company' first
if 'Company' in df.columns:
    cols = df.columns.tolist()
    cols.insert(0, cols.pop(cols.index('Company')))  # move 'Company' to first position
    df = df[cols]


# ---------------- GROUP BY DATE + SORTING ----------------
if 'result_posted_date' in df.columns and not df.empty:
    st.write(f"### Total Rows: **{len(df)}**")
    unique_dates = sorted(df['result_posted_date'].unique(), reverse=True)
    for d in unique_dates:
        group_df = df[df['result_posted_date'] == d].copy()
        if sort_choice == "Quarterly Difference (diff_qtr)" and 'diff_qtr' in group_df.columns:
            group_df = group_df.sort_values(by="diff_qtr", ascending=False)

        st.markdown(f"## 📅 {d}")
        st.markdown(
            tabulate(group_df, headers='keys', tablefmt='github', showindex=False),
            unsafe_allow_html=True
        )
        st.markdown("---")
else:
    st.markdown("No data to display for selected filters.")

conn.close()

