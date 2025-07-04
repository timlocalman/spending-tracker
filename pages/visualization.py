import streamlit as st
st.set_page_config(page_title="Spending Analytics", layout="wide")

from shared import load_all_data, refresh_data, category_budgets ,load_transaction_metadata
import pandas as pd
import pydeck as pdk
import altair as alt
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ✅ Refresh Button (top-level, not nested)
if st.button("🔄 Refresh Data"):
    refresh_data()

# ✅ Load data AFTER refresh
df = pd.DataFrame(load_all_data())
st.title("📊 Spending Visualizations")

df["DATE_dt"] = pd.to_datetime(df["DATE"], format="%m/%d/%Y", errors='coerce')
df["Amount Spent"] = pd.to_numeric(df["Amount Spent"], errors="coerce")
df = df[df["ITEM CATEGORY"].str.lower().isin([c.lower() for c in category_budgets if c.lower() not in ["savings", "income"]])]

# --- Weekly Spending Bar Chart ---
st.markdown("## 📅 Weekly Spending")
today = datetime.now().date()
week_start = today - timedelta(days=today.weekday())
df_week = df[(df["DATE_dt"].dt.date >= week_start) & (df["DATE_dt"].dt.date <= today)]
if not df_week.empty:
    chart_data = df_week.groupby("DATE_dt")["Amount Spent"].sum().reset_index()
    chart_data["Day"] = chart_data["DATE_dt"].dt.strftime("%a")
    bar_chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X("Day:N", sort=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]),
        y="Amount Spent:Q",
        tooltip=["Day", "Amount Spent"]
    ).properties(title="Daily Spending", height=250)
    st.altair_chart(bar_chart, use_container_width=True)
else:
    st.info("ℹ️ No data for this week yet.")
st.markdown("---")
# --- Today's Breakdown Pie Chart ---
st.markdown("## 📌 Today's Spending Breakdown")
today_str = f"{datetime.now().month}/{datetime.now().day}/{datetime.now().year}"
df_today = df[df["DATE"] == today_str]
pie_data = df_today.groupby("ITEM")["Amount Spent"].sum().reset_index()
if not pie_data.empty:
    pie_chart = alt.Chart(pie_data).mark_arc(innerRadius=50).encode(
        theta="Amount Spent:Q", color="ITEM:N", tooltip=["ITEM", "Amount Spent"]
    ).properties(height=350)
    st.altair_chart(pie_chart, use_container_width=True)
else:
    st.info("ℹ️ No spending recorded today.")
st.markdown("---")    
# --- Weekly Box Plot ---
st.markdown("## 📦 Weekly Spending Distribution (Box Plot)")
df_box = df_week.dropna(subset=["ITEM CATEGORY", "Amount Spent"])
if not df_box.empty:
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.boxplot(data=df_box, x="ITEM CATEGORY", y="Amount Spent", ax=ax)
    ax.set_title("Weekly Spending Distribution by Category")
    ax.set_xlabel("Category")
    ax.set_ylabel("Amount Spent")
    plt.xticks(rotation=45)
    st.pyplot(fig)
else:
    st.info("ℹ️ Not enough data for this week's box plot.")
st.markdown("---")
meta_df=pd.DataFrame(load_transaction_metadata())
meta_df["LAT"] = pd.to_numeric(meta_df["LAT"], errors="coerce")
meta_df["LON"] = pd.to_numeric(meta_df["LON"], errors="coerce")
meta_df = meta_df.dropna(subset=["LAT", "LON"])

# Optional: Merge with main df to get category or amount info
df_main = pd.DataFrame(load_all_data())
df_main["No"] = df_main["No"].astype(str)
meta_df["No"] = meta_df["No"].astype(str)

map_df = pd.merge(meta_df, df_main, on=["DATE", "No"], how="left")

if not map_df.empty:
    st.markdown("### 📍 Spending Locations Map")
    
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position='[LON, LAT]',
        get_radius=100,
        get_fill_color='[255, 140, 0, 160]',
        pickable=True,
        tooltip=True
    )

    tooltip = {
        "html": """
        <b>Location:</b> {LOCATION} <br/>
        <b>Item:</b> {ITEM} <br/>
        <b>Category:</b> {ITEM CATEGORY} <br/>
        <b>Amount:</b> ₦{Amount Spent} <br/>
        <b>Date:</b> {DATE}
        """,
        "style": {"backgroundColor": "steelblue", "color": "white"}
    }

    view_state = pdk.ViewState(
        latitude=map_df["LAT"].mean(),
        longitude=map_df["LON"].mean(),
        zoom=11,
        pitch=0
    )

    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip))
else:
    st.info("ℹ No location-tagged transactions yet.")

st.markdown("### 🔥 Top Spending Hotspots")

hotspots = map_df.groupby("LOCATION").agg({
    "Amount Spent": "sum",
    "DATE": "max",
    "No": "count"
}).rename(columns={
    "Amount Spent": "Total Spent",
    "DATE": "Last Visit",
    "No": "Visit Count"
}).sort_values("Visit Count", ascending=False).reset_index()

st.dataframe(hotspots.style.format({
    "Total Spent": "₦{:.0f}",
    "Last Visit": lambda d: pd.to_datetime(d).strftime("%b %d, %Y")
}))

