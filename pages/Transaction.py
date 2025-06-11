import streamlit as st
st.set_page_config(page_title="Spending Tracker - Home", layout="wide")

import pandas as pd
from datetime import datetime
from shared import (
    category_budgets, load_all_data, refresh_data,
    get_today_total_amount, get_weekly_total_amount, get_monthly_total_amount
)

# Refresh button
if st.button("🔄 Refresh Data", use_container_width=True):
    refresh_data()

# Load data
df = pd.DataFrame(load_all_data())
df["Amount Spent"] = pd.to_numeric(df["Amount Spent"], errors="coerce")
df["DATE_dt"] = pd.to_datetime(df["DATE"], format="%m/%d/%Y", errors='coerce')

st.title("📋 Transaction Records")

# --- METRICS ---
with st.container():
    col1, col2, col3 = st.columns(3)
    col1.metric("🗓️ Today", f"₦{get_today_total_amount():,.2f}")
    col2.metric("📅 This Week", f"₦{get_weekly_total_amount():,.2f}")
    col3.metric("📆 This Month", f"₦{get_monthly_total_amount():,.2f}")
st.markdown("---")

# --- MONTHLY BUDGET USAGE ---
total_month = get_monthly_total_amount()
total_budget = sum(v for k, v in category_budgets.items() if k.lower() not in ["savings", "income"])
percent_used = total_month / total_budget if total_budget > 0 else 0
st.markdown("### 🏁 Monthly Budget Usage")
st.progress(min(percent_used, 1.0), text=f"₦{total_month:,.0f} of ₦{total_budget:,.0f} used ({percent_used*100:.1f}%)")
st.markdown("---")

# --- TODAY'S TRANSACTIONS ---
st.markdown("### 📋 Today's Transactions")
today_str = f"{datetime.now().month}/{datetime.now().day}/{datetime.now().year}"
df_today = df[df["DATE"] == today_str]

if not df_today.empty:
    st.dataframe(
        df_today[["TIME", "ITEM", "ITEM CATEGORY", "No of ITEM", "Amount Spent"]],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("ℹ️ No transactions recorded yet today.")

st.markdown("---")

# --- LAST TIME EACH ITEM WAS BOUGHT ---
st.markdown("### 📅 Last Time Each Item Was Bought (by Category)")

all_categories = sorted(df["ITEM CATEGORY"].dropna().unique())
selected_cat = st.selectbox("📂 Select Category", all_categories)

if selected_cat:
    df_cat = df[df["ITEM CATEGORY"] == selected_cat]
    last_purchase = df_cat.groupby("ITEM")["DATE_dt"].max().reset_index()
    last_purchase["Last Bought"] = last_purchase["DATE_dt"].dt.strftime("%B %d")
    last_purchase = last_purchase[["ITEM", "Last Bought"]].rename(columns={"ITEM": "Item"})

    if not last_purchase.empty:
        st.dataframe(
            last_purchase.sort_values("Last Bought", ascending=False),
            use_container_width=True
        )
    else:
        st.info("ℹ️ No purchases found in this category.")
