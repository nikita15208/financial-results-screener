
import sqlite3

# Connect to the database
conn = sqlite3.connect('screener_data.db')
cursor = conn.cursor()

# Get all table names in the database
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

# Drop each table
for table_name in tables:
    table = table_name[0]  # fetch the string from tuple
    cursor.execute(f"DROP TABLE IF EXISTS {table}")
    print(f"Table '{table}' dropped successfully.")

# Commit and close
conn.commit()
conn.close()
print("All tables have been dropped.")

'''

import sqlite3

conn = sqlite3.connect('screener_data.db')
cursor = conn.cursor()

# List all tables in the database
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
conn.close()

print(tables)
'''
'''
import sqlite3
import pandas as pd

# Connect to the database
conn = sqlite3.connect('screener_data.db')

# Count total rows
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM company_results")
total_rows = cursor.fetchone()[0]
print(f"Total rows in company_results: {total_rows}\n")

# Fetch top 20 rows
df_top20 = pd.read_sql_query("SELECT * FROM company_results LIMIT 20", conn)
print("Top 20 rows in company_results:")
print(df_top20)

# Close connection
conn.close()
'''
'''
import sqlite3
import pandas as pd

# Connect to the database
conn = sqlite3.connect('screener_data.db')

# Count total rows
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM company_results")
total_rows = cursor.fetchone()[0]
print(f"Total rows in company_results: {total_rows}\n")

# Fetch top 20 rows with all columns
df_top20 = pd.read_sql_query("SELECT company, company_link, price, mcap, np_qtr, np_prev_qtr, np_last_year, scraped_date FROM company_results LIMIT 20", conn)

# Display all columns
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

print("Top 20 rows in company_results:")
print(df_top20)

# Close connection
conn.close()
'''
'''
import sqlite3
conn = sqlite3.connect('screener_data.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("📊 ROW COUNT IN EACH TABLE")
print("---------------------------------------")
for table in tables:
    table_name = table[0]
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"{table_name}: {count} rows")

conn.close()

'''
'''

import requests
from bs4 import BeautifulSoup

url = "https://www.screener.in/company/536659/#quarters"
r = requests.get(url)
soup = BeautifulSoup(r.text, "html.parser")
print(soup.prettify()[:2000])  # print first 2000 chars to see structure
'''

'''
from selenium import webdriver
from bs4 import BeautifulSoup
import time

url = "https://www.screener.in/company/536659/#quarters"

driver = webdriver.Chrome()  # Make sure chromedriver is installed
driver.get(url)
time.sleep(3)  # wait for JS to load

html = driver.page_source
soup = BeautifulSoup(html, "html.parser")

table = soup.find("table", {"class": "data-table"})
print(table)
driver.quit()

'''
