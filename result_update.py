# Enhanced result_update.py (modified for robust Net Profit extraction)
# Scrape Screener and save cleaned data to SQL
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
import time
import re # Added for robust text cleaning

# --- URLs and credentials ---
login_URL = 'https://www.screener.in/login/'
base_data_URL = 'https://www.screener.in/results/latest/'

# NOTE: Replace with actual credentials
import os

form_data = {
    'username': os.getenv("SCREENER_USERNAME"),
    'password': os.getenv("SCREENER_PASSWORD")
}

# Config
form_csrf_key = 'csrfmiddlewaretoken'
user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324'

# Helper function to clean and convert text to float
def clean_to_float(text):
    """Safely converts a string (like "₹ 1,234.56" or "—") to a float.
       Keeps minus sign for negatives and decimal point.
       Returns None for empty / non-numeric values.
    """
    if text is None:
        return None

    s = str(text).strip()

    # Common empties
    if s in ['', 'None', '—', '–', '-']:
        return None

    # Remove rupee symbol, commas, non-digit characters except minus and dot
    # Step1: remove common currency symbols and whitespace
    s = s.replace('₹', '').replace('Rs.', '').replace('Cr', '').replace('cr', '')
    s = s.replace(',', '').strip()

    # Step2: remove anything that is not digit, dot or minus
    s = re.sub(r'[^0-9\.\-]', '', s)

    # guard against stray values
    if s in ['', '-', '.', '-.']:
        return None

    try:
        return float(s)
    except ValueError:
        return None

# --- Start session and login ---
session = requests.Session()
login_page = session.get(login_URL)
soup = BeautifulSoup(login_page.text, 'html.parser')

# Safety check for CSRF token
csrf_input = soup.find('input', {'name': form_csrf_key})
if csrf_input and csrf_input.has_attr('value'):
    form_data[form_csrf_key] = csrf_input['value']
    print("Found CSRF token. Attempting login...")
else:
    print("Warning: Could not find CSRF token. Login may fail.")

session.post(login_URL, data=form_data, headers={'User-Agent': user_agent, 'Referer': login_URL})
print("Login attempt complete.")

# --- Current date helper ---
today = datetime.now()
current_year = today.year
current_month = today.month

def get_current_quarter_months():
    if current_month in [4,5,6]: return [4,5,6]
    elif current_month in [7,8,9]: return [7,8,9]
    elif current_month in [10,11,12]: return [10,11,12]
    else: return [1,2,3]

months_to_check = get_current_quarter_months()

# --- Connect to SQLite and create tables ---
conn = sqlite3.connect('screener_data.db')
cursor = conn.cursor()

# CRITICAL CHANGE 1: Standardized column name to 'market_cap'
cursor.execute("""
CREATE TABLE IF NOT EXISTS company_results (
    company TEXT,
    company_link TEXT,
    price REAL,
    market_cap REAL,
    np_qtr REAL,
    np_prev_qtr REAL,
    np_last_year REAL,
    scraped_date TEXT,
    PRIMARY KEY (company, scraped_date)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS last_scraped (
    last_scraped_date TEXT
)
""")
conn.commit()

# --- Determine start date ---
cursor.execute("SELECT last_scraped_date FROM last_scraped ORDER BY last_scraped_date DESC LIMIT 1")
last_date_row = cursor.fetchone()
if last_date_row and last_date_row[0]:
    t = datetime.strptime(last_date_row[0], '%Y-%m-%d') + timedelta(days=1)
else:
    t = datetime(current_year, months_to_check[0], 1)

# --- Scraping loop ---
result_update = []
print(f"Starting scrape from: {t.strftime('%Y-%m-%d')}")

while t <= today:
    day, month, year = t.day, t.month, t.year
    page = 1
    
    found_data_on_day = False 

    while True:
        url = f"{base_data_URL}?p={page}&result_update_date__day={day}&result_update_date__month={month}&result_update_date__year={year}"
        print(f"Scraping: {url} (Page {page})")
        
        try:
            response = session.get(url, headers={'User-Agent': user_agent})
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error accessing {url}: {e}")
            break

        soup = BeautifulSoup(response.text, 'html.parser')

        company_divs = soup.find_all(
            "div",
            class_="flex-row flex-space-between flex-align-center margin-top-32 margin-bottom-16 margin-left-4 margin-right-4"
        )
        if not company_divs:
            break

        found_data_on_day = True

        for div in company_divs:
            name_span = div.find("span", class_="hover-link ink-900")
            company_name = name_span.get_text(strip=True) if name_span else None
            link_span = div.find("a", class_="font-weight-500")
            company_link = link_span['href'].strip() if link_span and link_span.has_attr('href') else None

            price_str = mcap_str = None
            info_div = div.find("div", class_="font-size-14")
            if info_div:
                strongs = info_div.find_all("span", class_="strong")
                if len(strongs) >= 1: price_str = strongs[0].text
                if len(strongs) >= 2: mcap_str = strongs[1].text
            
            # CRITICAL CHANGE 2: Use robust cleaning function
            price = clean_to_float(price_str)
            market_cap = clean_to_float(mcap_str)

            # --- Robust Net Profit extraction ---
            np_qtr = np_prev_qtr = np_last_year = None
            table_div = div.find_next_sibling("div", class_="bg-base border-radius-8 padding-small responsive-holder")
            if table_div:
                table = table_div.find("table", class_="data-table")
                if table:
                    # Correct attribute matching for <tr data-net-profit>
                    np_row = table.find("tr", attrs={"data-net-profit": True})
                    if np_row:
                        tds = np_row.find_all("td")

                        # Prefer explicit attribute for latest quarter cell
                        latest_idx = None
                        for i, td in enumerate(tds):
                            if td.has_attr('data-np-latest-quarter'):
                                latest_idx = i
                                break

                        # Fallback: if attribute missing, pick the first numeric-looking td after label & YOY
                        if latest_idx is None:
                            # label usually at index 0, YOY at index 1 -> start from index 2
                            for i in range(2, len(tds)):
                                txt = tds[i].get_text(strip=True)
                                if re.search(r'[\d\-]', txt):  # simple numeric presence check
                                    latest_idx = i
                                    break

                        if latest_idx is not None:
                            def get_td_float(idx):
                                if 0 <= idx < len(tds):
                                    return clean_to_float(tds[idx].get_text(strip=True))
                                return None

                            # Latest quarter, Prev quarter (next column), Last year (next next)
                            np_qtr = get_td_float(latest_idx)
                            np_prev_qtr = get_td_float(latest_idx + 1)
                            np_last_year = get_td_float(latest_idx + 2)

            result_update.append({
                "company": company_name,
                "company_link": company_link,
                "price": price,
                "market_cap": market_cap,
                "np_qtr": np_qtr,
                "np_prev_qtr": np_prev_qtr,
                "np_last_year": np_last_year,
                "scraped_date": t.strftime('%Y-%m-%d')
            })

        paginator = soup.find("p", class_="paginator")
        next_page_link = soup.find("a", text=str(page + 1))
        
        if next_page_link:
            page += 1
            time.sleep(1)
        else:
            break

    # Advance to the next day
    t += timedelta(days=1)
    time.sleep(2)

# --- Convert list to DataFrame ---
if result_update:
    df_new = pd.DataFrame(result_update)
else:
    print("No new results scraped. Exiting.")
    conn.close()
    exit()

# --- Connect to SQLite ---
conn = sqlite3.connect('screener_data.db')
cursor = conn.cursor()

# --- Append new scraped data to company_results ---
df_new.to_sql("company_results", conn, if_exists="append", index=False)
print(f"Successfully appended {len(df_new)} new potential entries.")

# --- Update last_scraped with today's date ---
last_scraped_date_in_data = df_new['scraped_date'].max() if not df_new.empty else today.strftime('%Y-%m-%d')

cursor.execute("DELETE FROM last_scraped")
cursor.execute("INSERT INTO last_scraped (last_scraped_date) VALUES (?)", (last_scraped_date_in_data,))
conn.commit()
conn.close()
print(f"Last scraped date updated to {last_scraped_date_in_data} successfully.")
