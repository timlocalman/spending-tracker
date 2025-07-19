import streamlit as st
from streamlit_geolocation import streamlit_geolocation
from shared import (
    category_budgets, Spending_Sheet, Meta_Sheet,
    load_all_data, load_item_category_map,
    get_today_count, recommend_items_for_today,
    refresh_data, save_transaction_metadata, load_transaction_metadata
)
from datetime import datetime, timedelta
import pandas as pd
import re

st.set_page_config(page_title="Spending Tracker - Entry", layout="wide")

# --- Refresh Button ---
if st.button("🔄 Refresh Data"):
    refresh_data()

# --- Load Existing Data ---
df = pd.DataFrame(load_all_data())
st.title("💸 Spending Tracker")
st.markdown("---")

# --- All Checkboxes Outside Form ---
col1, col2, col3 = st.columns(3)
with col1:
    use_current_time = st.checkbox("🕒 Use Current Time (UTC+1)", value=False)
with col2:
    use_last_location = st.checkbox("📍 Use Last Location", value=False)
with col3:
    manual_entry = st.checkbox("📝 Enter total amount manually?", key="manual_toggle")

# --- Get Geolocation ---
st.markdown("#### 📡 Getting GPS Location...")
location = streamlit_geolocation()

lat = location.get("latitude") if location else None
lon = location.get("longitude") if location else None

if lat is not None and lon is not None:
    st.success(f"📍 Location captured: ({lat:.5f}, {lon:.5f})")
    st.session_state["lat"] = lat
    st.session_state["lon"] = lon
else:
    st.warning("⚠ Could not retrieve GPS coordinates. Please allow location access.")

# --- Transaction Form ---
with st.form("entry_form", clear_on_submit=True):
    # Prefill time if checkbox is checked
    if use_current_time:
        st.session_state["prefill_time"] = (datetime.utcnow() + timedelta(hours=1)).strftime("%H:%M")
    else:
        st.session_state.pop("prefill_time", None)
    
    selected_date = st.date_input("📆 Date", datetime.today())
    time_input = st.text_input(
        "⏰ Time (HH:MM)", 
        value=st.session_state.get("prefill_time", ""), 
        disabled=use_current_time
    )
    
    item = st.text_input("🛒 Item", value=st.session_state.get("prefill_item", "")).strip()

    # Category Prediction
    item_map = load_item_category_map()
    predicted = item_map.get(item.lower(), "Select Category")
    categories = ["Select Category"] + list(category_budgets.keys())
    category = st.radio("📂 Category", categories, index=categories.index(predicted) if predicted in categories else 0, horizontal=True)

    qty = st.slider("🔢 Quantity", 1, 10, 1)

    # Amount input based on manual_entry checkbox
    if manual_entry:
        amount = st.number_input("💸 Total Amount", min_value=0.0, step=0.01, key="manual_amt")
        st.caption(f"Manual total for {qty} unit(s)")
    else:
        unit_price = st.number_input("💰 Price per Unit", min_value=0.0, step=0.01, key="unit_price")
        amount = qty * unit_price
        st.info(f"Auto total: ₦{amount:,.2f}")
    
    payment_type = st.radio("💳 Payment Type", ["Cash", "Transfer", "Card"], horizontal=True)
    
    # Location Input (after payment type)
    if use_last_location:
        last_location = st.session_state.get("last_location", "")
        if not last_location and not df.empty:
            meta_df = pd.DataFrame(load_transaction_metadata())
            if not meta_df.empty:
                last_location = meta_df.iloc[-1]["LOCATION"]
        location_name = st.text_input(
            "📍 Location", 
            value=last_location,
            disabled=True
        )
    else:
        location_name = st.text_input("📍 Location")
    
    submitted = st.form_submit_button("✅ Submit")

# --- Handle Submission ---
if submitted:
    if not re.fullmatch(r"[0-9]{1,2}:[0-9]{2}", time_input):
        st.warning("⚠ Invalid time format (HH:MM).")
    elif category == "Select Category":
        st.warning("⚠ Please select a valid category.")
    elif not item:
        st.warning("⚠ Item name is required.")
    elif amount <= 0:
        st.warning("⚠ Amount must be greater than ₦0.")
    elif not location_name:
        st.warning("⚠ Please enter a location name.")
    elif lat is None or lon is None:
        st.warning("⚠ Could not retrieve GPS coordinates. Please allow location access.")
    else:
        DATE = f"{selected_date.month}/{selected_date.day}/{selected_date.year}"
        NO = get_today_count() + 1

        # Save to Sheets
        Spending_Sheet.append_row([
            DATE, NO, time_input, item, category, qty, amount,
            f"{(datetime.now().date() - timedelta(days=datetime.now().weekday())).day}-{datetime.now().strftime('%b')}",
            datetime.now().strftime("%B %Y")
        ])
        save_transaction_metadata(DATE, NO, location_name, lat, lon, payment_type)

        # Store last location in session state
        st.session_state["last_location"] = location_name

        st.cache_data.clear()
        st.success("✅ Transaction submitted!")

        # Confirmation sound
        st.markdown(
            """
            <audio autoplay>
             <source src="https://actions.google.com/sounds/v1/cartoon/wood_plank_flicks.ogg" type="audio/ogg">
            </audio>
            """,
            unsafe_allow_html=True
        )

        if amount >= 500:
            st.warning(f"🚨 Big purchase alert: ₦{amount:,.2f}")

        # Clear prefill state
        for k in ["prefill_item", "prefill_time", "manual_amt", "unit_price"]:
            st.session_state.pop(k, None)

st.markdown("---")

# --- TODAY'S TRANSACTIONS ---
st.markdown("### 📋 Today's Transactions")

today_str = f"{datetime.now().month}/{datetime.now().day}/{datetime.now().year}"
df_today = df[df["DATE"] == today_str]

# Load metadata and merge to get LOCATION
meta_df = pd.DataFrame(load_transaction_metadata())
meta_df["No"] = meta_df["No"].astype(str)
df_today["No"] = df_today["No"].astype(str)
df_today_loc = pd.merge(df_today, meta_df[["DATE", "No", "LOCATION"]], on=["DATE", "No"], how="left")

if not df_today_loc.empty:
    st.dataframe(
        df_today_loc[["TIME", "ITEM", "ITEM CATEGORY", "No of ITEM", "Amount Spent", "LOCATION"]],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("ℹ No transactions recorded yet today.")