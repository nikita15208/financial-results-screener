# ------------------ STEP 1: CLASSIFY FUNCTION ------------------

def classify_switches(df):
    """
    Classifies rows into Digit Switch and Initial Switch
    based on NP Qtr Rs.Cr. and NP Prev Qtr Rs.Cr.
    """

    # Helper function to count digits
    def count_digits(value):
        if value is None:
            return 0
        return len(str(int(abs(value)))) if value >= 0 else 0

    # Helper function to extract first digit
    def get_first_digit(value):
        if value is None:
            return -1
        return int(str(int(abs(value)))[0]) if value >= 0 else -1

    # Filter only rows with growth
    growth_df = df[df['np_qtr'] > df['np_prev_qtr']].copy()

    # Compute digit counts
    growth_df['Qtr_Digits'] = growth_df['np_qtr'].apply(count_digits)
    growth_df['Prev_Qtr_Digits'] = growth_df['np_prev_qtr'].apply(count_digits)

    # Compute first digits
    growth_df['Qtr_First_Digit'] = growth_df['np_qtr'].apply(get_first_digit)
    growth_df['Prev_Qtr_First_Digit'] = growth_df['np_prev_qtr'].apply(get_first_digit)

    # Digit Switch
    digit_switch_df = growth_df[
        growth_df['Qtr_Digits'] > growth_df['Prev_Qtr_Digits']
    ].copy()

    # Initial Switch
    initial_switch_df = growth_df[
        (growth_df['Qtr_Digits'] == growth_df['Prev_Qtr_Digits']) &
        (growth_df['Qtr_First_Digit'] > growth_df['Prev_Qtr_First_Digit'])
    ].copy()

    return digit_switch_df, initial_switch_df


# ------------------ STEP 2: CREATE Diff_Qtr & UPDATE DB ------------------

import sqlite3
import pandas as pd

conn = sqlite3.connect('screener_data.db')

# Load company_results
df = pd.read_sql_query("SELECT * FROM company_results", conn)

# Ensure required columns exist
required = ['np_qtr', 'np_prev_qtr']
for col in required:
    if col not in df.columns:
        print(f"ERROR: Required column missing → {col}")
        conn.close()
        exit()


df['np_qtr'] = pd.to_numeric(df['np_qtr'], errors='coerce')
df['np_prev_qtr'] = pd.to_numeric(df['np_prev_qtr'], errors='coerce')

# Create Diff_Qtr
df['diff_qtr'] = df['np_qtr'] - df['np_prev_qtr']

# Save updated table back
df.to_sql('company_results', conn, if_exists='replace', index=False)
df.to_excel('companu_results.xlsx', index=False)
print("Updated company_results with diff_qtr.")


# ------------------ STEP 3: CLASSIFY & SAVE TABLES ------------------

digit_switch_df, initial_switch_df = classify_switches(df)

# Select columns for output
common_cols = [
    'company', 'company_link', 'price', 'market_cap',
    'np_qtr', 'np_prev_qtr', 'np_last_year', 'scraped_date', 'diff_qtr'
]

# filter only existing columns
digit_switch_df = digit_switch_df[[c for c in common_cols if c in digit_switch_df.columns]]
initial_switch_df = initial_switch_df[[c for c in common_cols if c in initial_switch_df.columns]]



# Save to SQL
digit_switch_df.to_sql('digit_switch', conn, if_exists='replace', index=False)
initial_switch_df.to_sql('initial_switch', conn, if_exists='replace', index=False)

conn.close()
digit_switch_df.to_excel('digit_switch.xlsx', index=False)
print("Digit & Initial Switch tables created successfully.")
