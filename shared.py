import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta

# --- CATEGORY BUDGETS ---
category_budgets = {
    "Bet": 3000, "Bill": 35000, "Data": 11000, "Food": 40000,
    "Foodstuff": 150000, "Money": 10000, "Object": 50000, "Snacks": 60000,
    "transfer": 300000, "income": 250000, "Airtime": 1000,
    "transport": 70000, "Savings": 400000,
}

# --- GOOGLE SHEETS AUTH ---
creds_dict = dict(st.secrets["gcp_service_account"])
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1Pugi_cuQw25_GsGpVQAyzjWuuOFRLmP8yGKaIb6unD0/edit")
Spending_Sheet = sheet.worksheet("My Spending Sheet")

# --- DATA LOADERS ---
@st.cache_data(ttl=600)
def load_all_data():
    return Spending_Sheet.get_all_records(expected_headers=[
        "DATE", "No", "TIME", "ITEM", "ITEM CATEGORY",
        "No of ITEM", "Amount Spent", "WEEK", "MONTH"
    ])

@st.cache_data(ttl=3600)
def load_item_category_map():
    all_data = load_all_data()
    return {row["ITEM"].strip().lower(): row["ITEM CATEGORY"].strip()
            for row in all_data if row["ITEM"] and row["ITEM CATEGORY"]}

# --- REFRESH FUNCTION ---
def refresh_data():
    st.cache_data.clear()
    st.rerun() 

# --- UTILITIES ---
def get_today_count():
    today_str = f"{datetime.now().month}/{datetime.now().day}/{datetime.now().year}"
    return sum(1 for row in load_all_data() if row.get("DATE") == today_str)

def get_total_amount_by_period(key, value):
    all_data = load_all_data()
    return sum(float(row.get("Amount Spent", 0)) for row in all_data
               if row.get(key) == value and row.get("ITEM CATEGORY", "").lower() not in ["savings", "income"])

def get_today_total_amount():
    return get_total_amount_by_period("DATE", f"{datetime.now().month}/{datetime.now().day}/{datetime.now().year}")

def get_weekly_total_amount():
    week_str = f"{(datetime.now() - timedelta(days=datetime.now().weekday())).day}-{datetime.now().strftime('%b')}"
    return get_total_amount_by_period("WEEK", week_str)

def get_monthly_total_amount():
    return get_total_amount_by_period("MONTH", datetime.now().strftime("%B %Y"))

def recommend_items_for_today(df, top_n=5):
    if df.empty:
        return []
    df["DATE_dt"] = pd.to_datetime(df["DATE"], format="%m/%d/%Y", errors='coerce')
    df["Weekday"] = df["DATE_dt"].dt.day_name()
    today_weekday = datetime.now().strftime("%A")
    df_today = df[df["Weekday"] == today_weekday]
    return df_today["ITEM"].str.strip().value_counts().head(top_n).index.tolist()
