import streamlit as st
import pandas as pd
from shared import load_all_data, category_budgets, refresh_data
from datetime import datetime
import altair as alt

st.set_page_config(page_title="📊 Spending Dashboard", layout="wide")

# --- Refresh Button ---
if st.button("🔄 Refresh Data"):
    refresh_data()

# --- Load and Prepare Data ---
df = pd.DataFrame(load_all_data())
df["DATE_dt"] = pd.to_datetime(df["DATE"], format="%m/%d/%Y", errors="coerce")
df["Amount Spent"] = pd.to_numeric(df["Amount Spent"], errors="coerce")
df["MONTH"] = df["DATE_dt"].dt.strftime("%B %Y")
df["TransactionType"] = df["ITEM CATEGORY"].apply(
    lambda x: "Revenue" if x.lower() in ["income", "savings"] else "Expense"
)

# --- Filters ---
st.markdown("### 🔍 Filter Selection")

available_months = sorted(df["MONTH"].dropna().unique(), key=lambda x: datetime.strptime(x, "%B %Y"), reverse=True)
available_categories = sorted(df["ITEM CATEGORY"].dropna().unique())

selected_month = st.radio(
    "📅 Select Month",
    options=available_months,
    index=0,
    horizontal=True
)

selected_category = st.radio(
    "📂 Select Category",
    options=["All"] + available_categories,
    index=0,
    horizontal=True
)

# --- Filter Data ---
if selected_category == "All":
    filtered_df = df[df["MONTH"] == selected_month]
else:
    filtered_df = df[(df["MONTH"] == selected_month) & (df["ITEM CATEGORY"] == selected_category)]

spending_df = filtered_df[filtered_df["TransactionType"] == "Expense"]
revenue_df = filtered_df[filtered_df["TransactionType"] == "Revenue"]

# --- Metrics ---
st.title("📊 Dashboard Overview")

total_spent = spending_df['Amount Spent'].sum()
total_revenue = revenue_df['Amount Spent'].sum()
cash_at_hand = total_revenue - total_spent

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Total Revenue", f"₦{total_revenue:,.0f}")
col2.metric("💸 Total Spent", f"₦{total_spent:,.0f}")
col3.metric("💵 Cash at Hand", f"₦{cash_at_hand:,.0f}")
col4.metric("🧾 Total Transactions", f"{len(filtered_df):,}")

# --- Line Chart: Daily Spend vs Revenue Balance ---
st.markdown("### 💰 Daily Spend vs Revenue Balance")
daily_summary = filtered_df.groupby(["DATE_dt", "TransactionType"])["Amount Spent"].sum().unstack(fill_value=0)
daily_summary = daily_summary.rename(columns={"Revenue": "Revenue", "Expense": "Daily Spend"})
daily_summary["Revenue"] = daily_summary.get("Revenue", 0)
daily_summary["Daily Spend"] = daily_summary.get("Daily Spend", 0)
daily_summary["Revenue Balance"] = (daily_summary["Revenue"] - daily_summary["Daily Spend"]).cumsum()
daily_summary = daily_summary.reset_index()

chart_df = daily_summary.melt(
    id_vars="DATE_dt", value_vars=["Daily Spend", "Revenue Balance"],
    var_name="Metric", value_name="Amount"
)

line_chart = alt.Chart(chart_df).mark_line(point=True).encode(
    x="DATE_dt:T",
    y="Amount:Q",
    color="Metric:N",
    tooltip=["DATE_dt:T", "Metric:N", "Amount:Q"]
).properties(height=350, title="📈 Daily Spend vs Revenue Balance")

st.altair_chart(line_chart, use_container_width=True)

# --- Daily Spending by Category ---
st.markdown("### 📊 Daily Spending by Category")
category_line_data = filtered_df.groupby(["DATE_dt", "ITEM CATEGORY"])["Amount Spent"].sum().reset_index()

category_chart = alt.Chart(category_line_data).mark_line(point=True).encode(
    x="DATE_dt:T",
    y="Amount Spent:Q",
    color="ITEM CATEGORY:N",
    tooltip=["DATE_dt:T", "ITEM CATEGORY", "Amount Spent"]
).properties(height=400, title="📈 Daily Spending by Category")

st.altair_chart(category_chart, use_container_width=True)

# --- Top 3 Spending Categories Trend ---
if selected_category == "All":
    st.markdown("### 🔝 Top 3 Spending Categories")
    top3 = spending_df.groupby("ITEM CATEGORY")["Amount Spent"].sum().nlargest(3).index.tolist()
    top3_df = spending_df[spending_df["ITEM CATEGORY"].isin(top3)]

    top3_line = alt.Chart(
        top3_df.groupby(["DATE_dt", "ITEM CATEGORY"])["Amount Spent"].sum().reset_index()
    ).mark_line(point=True).encode(
        x="DATE_dt:T",
        y="Amount Spent:Q",
        color="ITEM CATEGORY:N",
        tooltip=["DATE_dt:T", "ITEM CATEGORY", "Amount Spent"]
    ).properties(height=300, title="📈 Trend of Top 3 Spending Categories")

    st.altair_chart(top3_line, use_container_width=True)

# --- Budget Utilization ---
st.markdown("### 🧮 Budget Category Utilization")
for cat, budget in category_budgets.items():
    if cat.lower() in ["income", "savings"]:
        continue
    if selected_category != "All" and cat != selected_category:
        continue

    spent = spending_df.loc[spending_df["ITEM CATEGORY"].str.lower() == cat.lower(), "Amount Spent"].sum()
    percent = spent / budget if budget else 0
    st.markdown(f"**{cat}** — ₦{spent:,.0f} / ₦{budget:,.0f} ({percent*100:.1f}%)")
    st.progress(min(percent, 1.0))

# --- Smart Alerts ---
st.markdown("### 🚨 Smart Alerts")
alerts = []
for cat, budget in category_budgets.items():
    if cat.lower() in ["income", "savings"]:
        continue
    if selected_category != "All" and cat != selected_category:
        continue

    spent = spending_df.loc[spending_df["ITEM CATEGORY"].str.lower() == cat.lower(), "Amount Spent"].sum()
    if spent > budget:
        alerts.append(f"🔴 **{cat}** is over budget by ₦{spent - budget:,.0f}")
    elif spent / budget > 0.75:
        alerts.append(f"🟠 **{cat}** is over 75% used.")

if alerts:
    for alert in alerts:
        st.warning(alert)
else:
    st.success("✅ No budget alerts. You're on track!")

# --- Calendar Heatmap ---
st.markdown("### 📅 Budget Calendar View (Heatmap)")
heatmap_df = filtered_df[filtered_df["TransactionType"] == "Expense"]
heatmap_df = heatmap_df.groupby("DATE_dt")["Amount Spent"].sum().reset_index()

# Fill in missing dates
month_start = datetime.strptime(selected_month, "%B %Y")
month_end = (month_start.replace(day=28) + pd.DateOffset(days=4)).replace(day=1) - pd.DateOffset(days=1)
all_days = pd.date_range(start=month_start, end=month_end, freq='D')
heatmap_df = pd.DataFrame({"DATE_dt": all_days}).merge(heatmap_df, on="DATE_dt", how="left").fillna(0)
heatmap_df["Weekday"] = heatmap_df["DATE_dt"].dt.weekday
heatmap_df["Week"] = heatmap_df["DATE_dt"].dt.isocalendar().week

# Normalize for color
max_spend = heatmap_df["Amount Spent"].max()

heatmap_chart = alt.Chart(heatmap_df).mark_rect().encode(
    x=alt.X("Week:O", title="Week Number"),
    y=alt.Y("Weekday:O", title=None,
            sort=alt.SortField("Weekday", order="ascending"),
            axis=alt.Axis(labels=True, values=list(range(7)),
                          labelExpr="['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][datum.value]")),
    color=alt.Color("Amount Spent:Q", scale=alt.Scale(scheme='greens', domain=[0, max_spend]), legend=None),
    tooltip=["DATE_dt:T", "Amount Spent:Q"]
).properties(
    width=700,
    height=140,
    title="🗓️ Daily Spending Heatmap"
)

st.altair_chart(heatmap_chart, use_container_width=True)
