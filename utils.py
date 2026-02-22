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
        allowance = 0
        spent = 0

        allowance = int(float(allowance or 0))
        carryover = int(float(carryover or 0))

        remaining = allowance + carryover
        # remaining = allowance + carryover

        get_balance_sheet().append_row([
            str(month_key),
            float(allowance),
            float(carryover),
            float(spent),
            float(remaining)
        ])

        return remaining

# # Log a new purchase
# def log_purchase(purchase_date, description, amount):
#     tx_sheet = get_transaction_sheet()
#     tx_sheet.append_row([
#         purchase_date.strftime("%Y-%m-%d"),  # DATE
#         purchase_date.strftime("%Y-%m"),     # MONTH
#         description,
#         amount
#     ])
#     # No need to update monthly_balances if formulas handle it

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


# Example signatures – align with your current Google Sheets helpers
def log_purchase(tx_date, description, amount):
    _append_transaction_row(tx_date, "PURCHASE", amount, description)
    _update_monthly_balance(tx_date, -abs(float(amount or 0)))

def log_bonus(tx_date, description, amount):
    _append_transaction_row(tx_date, "BONUS", amount, description)
    _update_monthly_balance(tx_date, abs(float(amount or 0)))

def _append_transaction_row(tx_date, tx_type, amount, description):
    # Normalize
    d = pd.to_datetime(tx_date).date()
    month_key = f"{d:%Y-%m}"

    row = {
        "DATE": f"{d:%Y-%m-%d}",
        "MONTH": month_key,
        "TYPE": tx_type,            # <-- NEW
        "AMOUNT": round(float(amount), 2),
        "DESCRIPTION": description or "",
    }
    tx_sheet = get_transaction_sheet()
    headers = tx_sheet.row_values(1)
    if headers:
        header_keys = [h.strip().upper() for h in headers]
        row_values = [row.get(key, "") for key in header_keys]
        tx_sheet.append_row(row_values, value_input_option="USER_ENTERED")
    else:
        tx_sheet.append_row(
            [row["DATE"], row["MONTH"], row["DESCRIPTION"], row["AMOUNT"]],
            value_input_option="USER_ENTERED",
        )


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _update_monthly_balance(tx_date, delta_amount):
    d = pd.to_datetime(tx_date).date()
    month_key = f"{d:%Y-%m}"
    balance_sheet = get_balance_sheet()
    headers = balance_sheet.row_values(1)
    if not headers:
        return

    header_keys = [h.strip().upper() for h in headers]
    if "MONTH" not in header_keys:
        return

    records = balance_sheet.get_all_records()
    df = pd.DataFrame(records)
    df_months = df["MONTH"].astype(str) if not df.empty and "MONTH" in df.columns else pd.Series(dtype=str)

    def header_index(col_name):
        return header_keys.index(col_name) + 1

    def update_cell(row_num, col_name, value):
        if col_name in header_keys:
            balance_sheet.update_cell(row_num, header_index(col_name), value)

    if not df.empty and month_key in df_months.values:
        row_idx = df_months[df_months == month_key].index[0]
        sheet_row = row_idx + 2
        row = df.iloc[row_idx]
        spent = _to_float(row.get("SPENT")) + max(0.0, -delta_amount)
        remaining = _to_float(row.get("REMAINING")) + delta_amount

        update_cell(sheet_row, "SPENT", round(spent, 2))
        update_cell(sheet_row, "REMAINING", round(remaining, 2))
        return

    carryover = 0.0
    if not df.empty and "REMAINING" in df.columns:
        carryover = _to_float(df.iloc[-1].get("REMAINING"))

    allowance = 0.0
    spent = max(0.0, -delta_amount)
    remaining = allowance + carryover + delta_amount

    row_map = {
        "MONTH": month_key,
        "ALLOWANCE": round(allowance, 2),
        "CARRYOVER": round(carryover, 2),
        "SPENT": round(spent, 2),
        "REMAINING": round(remaining, 2),
    }

    row_values = [row_map.get(key, "") for key in header_keys]
    balance_sheet.append_row(row_values, value_input_option="USER_ENTERED")
