import streamlit as st
import pandas as pd
from shared import load_all_data, category_budgets, refresh_data
from datetime import datetime
import altair as alt

# Mobile-responsive CSS
st.markdown("""
<style>
@media screen and (max-width: 600px) {
    /* Adjust font sizes */
    h1 {font-size: 1.5rem !important;}
    h2 {font-size: 1.2rem !important;}
    h3 {font-size: 1.1rem !important;}
    .stMetricLabel {font-size: 0.9rem !important;}
    .stMetricValue {font-size: 1.1rem !important;}
    
    /* Reduce padding */
    .main .block-container {
        padding: 1rem 1rem 5rem 1rem;
    }
    
    /* Make buttons more touch-friendly */
    .stButton>button {
        width: 100%;
        padding: 0.5rem;
    }
    
    /* Adjust select boxes */
    .stSelectbox>div>div>select {
        font-size: 0.9rem;
    }
}

/* General improvements */
.stMetric {
    padding: 0.5rem !important;
    border-radius: 0.5rem;
    background-color: #f0f2f6;
}
</style>
""", unsafe_allow_html=True)

st.set_page_config(
    page_title="📊 Spending Dashboard", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Refresh Button ---
if st.button("🔄 Refresh Data", use_container_width=True):
    refresh_data()
    st.rerun()

# --- Load and Prepare Data ---
df = pd.DataFrame(load_all_data())
df["DATE_dt"] = pd.to_datetime(df["DATE"], format="%m/%d/%Y", errors="coerce")
df["Amount Spent"] = pd.to_numeric(df["Amount Spent"], errors="coerce")
df["MONTH"] = df["DATE_dt"].dt.strftime("%B %Y")
df["TransactionType"] = df["ITEM CATEGORY"].apply(
    lambda x: "Revenue" if x.lower() in ["income", "savings"] else "Expense"
)

# --- Mobile-Friendly Filters ---
available_months = sorted(df["MONTH"].dropna().unique(), key=lambda x: datetime.strptime(x, "%B %Y"), reverse=True)
available_categories = sorted(df["ITEM CATEGORY"].dropna().unique())

with st.expander("🔍 Filter Options", expanded=True):
    selected_month = st.selectbox(
        "📅 Select Month",
        options=available_months,
        index=0
    )
    
    selected_category = st.selectbox(
        "📂 Select Category",
        options=["All"] + available_categories,
        index=0
    )

# --- Filter Data ---
if selected_category == "All":
    filtered_df = df[df["MONTH"] == selected_month]
else:
    filtered_df = df[(df["MONTH"] == selected_month) & (df["ITEM CATEGORY"] == selected_category)]

spending_df = filtered_df[filtered_df["TransactionType"] == "Expense"]
revenue_df = filtered_df[filtered_df["TransactionType"] == "Revenue"]

# --- Mobile-Optimized Metrics ---
st.title("📊 Dashboard Overview")

col1, col2 = st.columns(2)
col3, col4 = st.columns(2)

total_spent = spending_df['Amount Spent'].sum()
total_revenue = revenue_df['Amount Spent'].sum()
cash_at_hand = total_revenue - total_spent

col1.metric("💰 Total Revenue", f"₦{total_revenue:,.0f}")
col2.metric("💸 Total Spent", f"₦{total_spent:,.0f}")
col3.metric("💵 Cash at Hand", f"₦{cash_at_hand:,.0f}")
col4.metric("🧾 Transactions", f"{len(filtered_df):,}")

# --- Simplified Line Chart ---
with st.expander("📈 Spending Trends", expanded=True):
    daily_summary = filtered_df.groupby(["DATE_dt", "TransactionType"])["Amount Spent"].sum().unstack(fill_value=0)
    daily_summary["Revenue Balance"] = (daily_summary.get("Revenue", 0) - daily_summary.get("Expense", 0)).cumsum()
    
    chart_df = daily_summary.reset_index().melt(
        id_vars="DATE_dt", 
        value_vars=["Expense", "Revenue Balance"],
        var_name="Metric", 
        value_name="Amount"
    )

    line_chart = alt.Chart(chart_df).mark_line(point=True).encode(
        x=alt.X("DATE_dt:T", title="Date"),
        y=alt.Y("Amount:Q", title="Amount (₦)"),
        color=alt.Color("Metric:N", legend=alt.Legend(title=None)),
        tooltip=["DATE_dt:T", "Metric:N", alt.Tooltip("Amount:Q", format=",.0f")]
    ).properties(
        height=250,
        width="container"
    )
    st.altair_chart(line_chart, use_container_width=True)

# --- Category Spending ---
with st.expander("📊 Category Breakdown", expanded=False):
    category_data = spending_df.groupby("ITEM CATEGORY")["Amount Spent"].sum().reset_index()
    category_data = category_data.sort_values("Amount Spent", ascending=False)
    
    bar_chart = alt.Chart(category_data).mark_bar().encode(
        y=alt.Y("ITEM CATEGORY:N", title="Category", sort="-x"),
        x=alt.X("Amount Spent:Q", title="Amount Spent (₦)"),
        tooltip=["ITEM CATEGORY", alt.Tooltip("Amount Spent:Q", format=",.0f")]
    ).properties(
        height=300,
        width="container"
    )
    st.altair_chart(bar_chart, use_container_width=True)

# --- Budget Tracking ---
with st.expander("🧮 Budget Tracking", expanded=False):
    for cat, budget in category_budgets.items():
        if cat.lower() in ["income", "savings"]:
            continue
        if selected_category != "All" and cat != selected_category:
            continue

        spent = spending_df.loc[spending_df["ITEM CATEGORY"].str.lower() == cat.lower(), "Amount Spent"].sum()
        percent = spent / budget if budget else 0
        
        st.write(f"**{cat}**")
        cols = st.columns([1, 4])
        cols[0].write(f"₦{spent:,.0f} / ₦{budget:,.0f}")
        cols[1].progress(min(percent, 1.0), f"{percent*100:.1f}%")

# --- Alerts ---
with st.expander("🚨 Budget Alerts", expanded=False):
    alerts = []
    for cat, budget in category_budgets.items():
        if cat.lower() in ["income", "savings"]:
            continue
        if selected_category != "All" and cat != selected_category:
            continue

        spent = spending_df.loc[spending_df["ITEM CATEGORY"].str.lower() == cat.lower(), "Amount Spent"].sum()
        if spent > budget:
            alerts.append(f"🔴 **{cat}** over by ₦{spent - budget:,.0f}")
        elif spent / budget > 0.75:
            alerts.append(f"🟠 **{cat}** at {percent*100:.1f}%")

    if alerts:
        for alert in alerts:
            st.warning(alert)
    else:
        st.success("✅ All budgets are on track")

# --- Calendar Heatmap (Simplified) ---
with st.expander("📅 Daily Overview", expanded=False):
    heatmap_df = filtered_df[filtered_df["TransactionType"] == "Expense"]
    heatmap_df = heatmap_df.groupby("DATE_dt")["Amount Spent"].sum().reset_index()
    
    # Fill missing dates
    month_start = datetime.strptime(selected_month, "%B %Y")
    month_end = (month_start.replace(day=28) + pd.DateOffset(days=4)).replace(day=1) - pd.DateOffset(days=1)
    all_days = pd.date_range(start=month_start, end=month_end, freq='D')
    heatmap_df = pd.DataFrame({"DATE_dt": all_days}).merge(heatmap_df, on="DATE_dt", how="left").fillna(0)
    
    heatmap_chart = alt.Chart(heatmap_df).mark_rect().encode(
        x=alt.X('date(DATE_dt):O', title='Day of Month'),
        y=alt.Y('monthdate(DATE_dt):O', title='Week'),
        color=alt.Color('Amount Spent:Q', scale=alt.Scale(scheme='greens'), legend=None),
        tooltip=['DATE_dt:T', alt.Tooltip('Amount Spent:Q', format=",.0f")]
    ).properties(
        height=200,
        width="container"
    )
    st.altair_chart(heatmap_chart, use_container_width=True)