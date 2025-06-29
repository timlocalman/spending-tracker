import streamlit as st
st.set_page_config(page_title="Spending Tracker - Entry", layout="wide")

from shared import (
    category_budgets, Spending_Sheet, load_all_data, load_item_category_map,
    get_today_count, recommend_items_for_today, refresh_data
)
from datetime import datetime, timedelta
import pandas as pd
import re

# Refresh button
if st.button("🔄 Refresh Data"):
    refresh_data()

# Load data
df = pd.DataFrame(load_all_data())
st.title("💸 Spending Tracker")

# --- Recommendations ---
df["Amount Spent"] = pd.to_numeric(df["Amount Spent"], errors="coerce")
likely_items = recommend_items_for_today(df)
if likely_items:
    st.markdown("### 🛒 Items You Might Buy Today")
    cols = st.columns(len(likely_items))
    for idx, item in enumerate(likely_items):
        if cols[idx].button(item):
            st.session_state["prefill_item"] = item

st.markdown("---")

# --- Time Selection Logic ---
st.markdown("#### 🕒 Time Selection (UTC+1)")
use_current_time = st.checkbox("🕒 Use Current Time (UTC+1)", value=False)
if use_current_time:
    current_time_str = (datetime.utcnow() + timedelta(hours=1)).strftime("%H:%M")
    st.session_state["prefill_time"] = current_time_str
else:
    st.session_state.pop("prefill_time", None)

# Checkbox for manual amount entry (outside form so it updates instantly)
manual_entry = st.checkbox("📝 Enter total amount manually?", key="manual_toggle")

# --- Transaction Entry Form ---
with st.form("entry_form", clear_on_submit=True):
    st.markdown("### ✍️ Add New Transaction")
    selected_date = st.date_input("📆 Date", datetime.today())

    time_input = st.text_input(
        "⏰ Time (e.g. 14:30)",
        value=st.session_state.get("prefill_time", ""),
        disabled=use_current_time
    )

    prefill_item = st.session_state.get("prefill_item", "")
    item = st.text_input("🛒 Item", value=prefill_item).strip()

    # Category input as horizontal radio buttons
    item_map = load_item_category_map()
    predicted_cat = item_map.get(item.lower(), "Select Category")
    cat_opts = ["Select Category"] + list(category_budgets.keys())
    category = st.radio(
        "📂 Category",
        cat_opts,
        index=cat_opts.index(predicted_cat) if predicted_cat in cat_opts else 0,
        horizontal=True
    )

    # Quantity slider input
    qty = st.slider("🔢 Quantity", min_value=1, max_value=10, value=1, step=1)

    if manual_entry:
        amount = st.number_input("💸 Total Amount", min_value=0.0, step=0.01, key="manual_amount")
        st.caption(f"💡 Total entered manually for quantity x {qty}")
    else:
        unit_price = st.number_input("💰 Price per Unit", min_value=0.0, step=0.01, key="unit_price")
        amount = qty * unit_price
        st.info(f"💵 Auto-calculated total = ₦{amount:,.2f}")

    # Submit logic
    if st.form_submit_button("✅ Submit"):
        if not re.fullmatch(r"[0-9:]+", time_input):
            st.warning("⚠️ Invalid time format.")
        elif category == "Select Category":
            st.warning("⚠️ Please select a valid category.")
        elif not item:
            st.warning("⚠️ Item name is required.")
        elif amount <= 0:
            st.warning("⚠️ Amount must be greater than ₦0.")
        else:
            row = [
                f"{selected_date.month}/{selected_date.day}/{selected_date.year}",
                get_today_count() + 1,
                time_input, item, category, qty, amount,
                f"{(datetime.now() - timedelta(days=datetime.now().weekday())).day}-{datetime.now().strftime('%b')}",
                datetime.now().strftime("%B %Y")
            ]
            Spending_Sheet.append_row(row)
            st.cache_data.clear()
            st.success("✅ Transaction submitted!")

            # 🎧 Audio confirmation
            st.markdown(
                """
                <audio id="success-sound" autoplay>
                  <source src="https://actions.google.com/sounds/v1/cartoon/wood_plank_flicks.ogg" type="audio/ogg">
                </audio>
                <script>
                const audio = document.getElementById("success-sound");
                if (audio) audio.play();
                </script>
                """,
                unsafe_allow_html=True
            )

            # ⚠️ Big purchase warning
            if amount >= 5000:
                st.warning("🚨 Big Purchase Alert! You just spent ₦{:,.2f}".format(amount))

            st.session_state.pop("prefill_item", None)
            st.session_state.pop("prefill_time", None)
