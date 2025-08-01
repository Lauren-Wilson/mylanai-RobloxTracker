import streamlit as st
from utils import get_balance, log_purchase, get_dashboard_data, get_balance_sheet
from datetime import date, datetime
import pandas as pd
import base64

# Set up navigation
st.set_page_config(page_title="Roblox Tracker", layout="wide")
page = st.sidebar.selectbox("Navigation", ["💰 Jar Balance", "📊 Dashboard"])

if page == "💰 Jar Balance":
    st.title("Roblox Allowance Jar")

    # Show jar image
    def get_base64_image(image_path):
        with open(image_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()

    jar_base64 = get_base64_image("assets/empty_jar.jpg")

    st.markdown(
        f"""
        <div style="text-align: center;">
            <img src="data:image/png;base64,{jar_base64}" alt="Jar" width="300"/>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Get current balance
    balance = get_balance()
    st.markdown(f"### Remaining: **${balance:.2f}** for {date.today().strftime('%B %Y')}")

    st.subheader("Log a Purchase")
    with st.form("log_purchase"):
        description = st.text_input("What was purchased?")
        amount = st.number_input("How much was spent?", min_value=0.0, step=0.01)
        purchase_date = st.date_input("Date", value=date.today())
        submit = st.form_submit_button("Add Purchase")

        if submit:
            log_purchase(purchase_date, description, amount)
            st.success("Purchase logged successfully!")

elif page == "📊 Dashboard":

    st.title("Roblox Spending Dashboard")

    # Get data
    monthly_summary, full_tx = get_dashboard_data()
    carry_df = pd.DataFrame(get_balance_sheet().get_all_records())

    if monthly_summary.empty or carry_df.empty:
        st.warning("No spending data yet.")
    else:

        # ─────────────────────────────
        # TIER 1: Core Financial Metrics
        # ─────────────────────────────
        st.markdown("## 💡 Tier 1: Key Financial Insights")

        # 📈 Line chart
        st.subheader("📈 Monthly Spending Over Time")
        st.line_chart(monthly_summary.set_index("MONTH")["TOTAL SPENT"])

        # 📊 Metric cards
        total_spent = full_tx["AMOUNT"].sum()
        highest_month = monthly_summary.loc[monthly_summary["TOTAL SPENT"].idxmax()]
        highest_spend = highest_month["TOTAL SPENT"]
        highest_month_label = highest_month["MONTH"]

        col1, col2 = st.columns(2)
        col1.metric("Lifetime Spend", f"${total_spent:.2f}")
        col2.metric("Highest Monthly Spend", f"${highest_spend:.2f}", highest_month_label)

        max_carry = carry_df["CARRYOVER"].max()
        max_month = carry_df.loc[carry_df["CARRYOVER"].idxmax()]["MONTH"]
        st.metric("Biggest Carryover", f"${max_carry:.2f}", max_month)

        # 🗓 Current Month Summary
        st.markdown("### 📅 Current Month Summary")
        current_month = datetime.today().strftime("%Y-%m")
        if current_month in carry_df["MONTH"].values:
            row = carry_df[carry_df["MONTH"] == current_month].iloc[0]
            st.info(
                f"**Allowance:** ${row['ALLOWANCE']}  \n"
                f"**Carryover:** ${row['CARRYOVER']}  \n"
                f"**Spent:** ${row['SPENT']}  \n"
                f"**Remaining:** ${row['REMAINING']}"
            )

        # 🧾 Recent Transactions
        st.markdown("### 🧾 Recent Transactions")
        st.dataframe(full_tx.sort_values(by="DATE", ascending=False).head(10))

        # ────────────────────────────────
        # TIER 2: Budgeting Behavior Metrics
        # ────────────────────────────────
        st.markdown("## 🧮 Tier 2: Budgeting Behavior")

        avg_spend = monthly_summary["TOTAL SPENT"].mean()
        st.metric("Average Monthly Spend", f"${avg_spend:.2f}")

        over_budget = monthly_summary[monthly_summary["TOTAL SPENT"] > 10]
        under_budget = monthly_summary[monthly_summary["TOTAL SPENT"] <= 10]
        col3, col4 = st.columns(2)
        col3.metric("Months Over Budget", len(over_budget))
        col4.metric("Months Under Budget", len(under_budget))

        monthly_summary["% CHANGE"] = monthly_summary["TOTAL SPENT"].pct_change().fillna(0) * 100
        st.markdown("### 🔄 Month-to-Month % Change")
        st.bar_chart(monthly_summary.set_index("MONTH")["% CHANGE"])

        purchase_counts = full_tx.groupby("MONTH").size().reset_index(name="PURCHASES")
        st.markdown("### 🛒 Purchases Per Month")
        st.bar_chart(purchase_counts.set_index("MONTH")["PURCHASES"])

        # ────────────────────────────────
        # TIER 3: Behavioral & Contextual Metrics
        # ────────────────────────────────
        st.markdown("## 🧠 Tier 3: Behavioral Insights")

        if "DESCRIPTION" in full_tx.columns:
            top_keywords = (
                full_tx["DESCRIPTION"]
                .str.lower()
                .str.extractall(r'(\w+)')[0]
                .value_counts()
                .head(5)
            )
            st.markdown("### 🔤 Top Purchase Keywords")
            st.bar_chart(top_keywords)

        if len(full_tx) < 2:
            st.info("Only one transaction logged — need at least two to calculate time between purchases.")

        full_tx["DATE"] = pd.to_datetime(full_tx["DATE"], errors="coerce")
        full_tx = full_tx.sort_values("DATE")
        full_tx["DAYS SINCE LAST"] = full_tx["DATE"].diff().dt.days
        longest_gap = full_tx["DAYS SINCE LAST"].max()

        if pd.isna(longest_gap):
            st.metric("Longest Gap Between Purchases", "N/A")
        else:
            st.metric("Longest Gap Between Purchases", f"{int(longest_gap)} days")


        first_dates = full_tx.groupby("MONTH")["DATE"].min().reset_index()
        st.markdown("### 📅 First Purchase Each Month")
        st.dataframe(first_dates)
