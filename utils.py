import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
client = gspread.authorize(creds)

# Sheet ID from secrets.toml
SHEET_ID = st.secrets["google_sheets"]["sheet_id"]

# Access worksheets
def get_balance_sheet():
    return client.open_by_key(SHEET_ID).worksheet("monthly_balances")

def get_transaction_sheet():
    return client.open_by_key(SHEET_ID).worksheet("transactions")

def get_current_month_key():
    today = datetime.today()
    return today.strftime("%Y-%m")

# Fetch current month's remaining balance
def get_balance():
    month_key = get_current_month_key()
    balances = get_balance_sheet().get_all_records()
    df = pd.DataFrame(balances)

    if month_key in df["MONTH"].values:
        row = df[df["MONTH"] == month_key].iloc[0]
        return row["REMAINING"]
    else:
        # Roll over previous month’s remaining
        last_row = df.iloc[-1] if not df.empty else {"REMAINING": 0}
        carryover = last_row["REMAINING"] if not df.empty else 0
        allowance = 10
        spent = 0
        remaining = allowance + carryover

        get_balance_sheet().append_row([
            str(month_key),
            float(allowance),
            float(carryover),
            float(spent),
            float(remaining)
        ])

        return remaining

# Log a new purchase
def log_purchase(purchase_date, description, amount):
    tx_sheet = get_transaction_sheet()
    tx_sheet.append_row([
        purchase_date.strftime("%Y-%m-%d"),  # DATE
        purchase_date.strftime("%Y-%m"),     # MONTH
        description,
        amount
    ])
    # No need to update monthly_balances if formulas handle it

# Generate dashboard chart data
def get_dashboard_data():
    tx_data = get_transaction_sheet().get_all_records()
    df = pd.DataFrame(tx_data)

    if df.empty:
        return pd.DataFrame(columns=["MONTH", "TOTAL SPENT"]), df

    df["AMOUNT"] = pd.to_numeric(df["AMOUNT"], errors="coerce")
    df["MONTH"] = df["MONTH"].astype(str)
    df = df.dropna(subset=["AMOUNT", "MONTH"])

    monthly_summary = df.groupby("MONTH")["AMOUNT"].sum().reset_index(name="TOTAL SPENT")
    return monthly_summary, df
