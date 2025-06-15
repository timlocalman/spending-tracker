import streamlit as st
st.set_page_config(page_title="Spending Analytics", layout="wide")

from shared import load_all_data, refresh_data, category_budgets
import pandas as pd
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

chart_view = st.selectbox(
    "📊 Select Chart",
    ["Weekly Spending", "Today's Breakdown", "Category Progress", "Spending Distribution (Box Plot)"]
)

if chart_view == "Weekly Spending":
    week_start = datetime.now() - timedelta(days=datetime.now().weekday())
    df_week = df[df["DATE_dt"].between(week_start, datetime.now())]
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

elif chart_view == "Today's Breakdown":
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

elif chart_view == "Category Progress":
    st.markdown("### 📂 Category Budget Tracking")
    df_month = df[df["MONTH"] == datetime.now().strftime("%B %Y")]
    cat_month = df_month.groupby("ITEM CATEGORY")["Amount Spent"].sum().reset_index()

    for cat, budget in category_budgets.items():
        if cat.lower() in ["savings", "income"]:
            continue
        spent = cat_month.loc[cat_month["ITEM CATEGORY"].str.lower() == cat.lower(), "Amount Spent"].sum()
        percent = spent / budget if budget > 0 else 0
        st.markdown(f"**{cat}** — ₦{spent:,.0f} / ₦{budget:,.0f} ({percent*100:.1f}%)")
        st.progress(min(percent, 1.0))

elif chart_view == "Spending Distribution (Box Plot)":
    st.markdown("### 📦 Weekly Box Plot of Spending by Category")

    # Filter to this week's data
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())  # Monday
    df_week = df[df["DATE_dt"].between(week_start, today)]

    # Drop rows with missing category or amount
    df_box = df_week.dropna(subset=["ITEM CATEGORY", "Amount Spent"])

    if not df_box.empty:
        import matplotlib.pyplot as plt
        import seaborn as sns

        fig, ax = plt.subplots(figsize=(10, 5))
        sns.boxplot(data=df_box, x="ITEM CATEGORY", y="Amount Spent", ax=ax)
        ax.set_title("Weekly Spending Distribution by Category")
        ax.set_xlabel("Category")
        ax.set_ylabel("Amount Spent")
        plt.xticks(rotation=45)
        st.pyplot(fig)
    else:
        st.info("ℹ️ Not enough data for this week's box plot.")