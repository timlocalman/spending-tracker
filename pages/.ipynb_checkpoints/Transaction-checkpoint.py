import streamlit as st
st.set_page_config(page_title="Spending Tracker - Home", layout="wide")

import pandas as pd
from datetime import datetime
from shared import load_all_data, refresh_data

# Refresh button
if st.button("🔄 Refresh Data", use_container_width=True):
    refresh_data()

# Load data
df = pd.DataFrame(load_all_data())
df["Amount Spent"] = pd.to_numeric(df["Amount Spent"], errors="coerce")
df["DATE_dt"] = pd.to_datetime(df["DATE"], format="%m/%d/%Y", errors='coerce')

st.title("📋 Transaction Records")

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
