# frontend/pages/3_Browse_Items.py
import sys
import os
import streamlit as st
import httpx

# Ensure parent directory is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import api_client
from app import load_css, check_auth
from components.item_card import render_item_card

check_auth()  # Navigation guard
load_css()

st.title("Browse available items")

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    
    # 1. Category Multiselect
    categories = ["Clothing", "Furniture", "Electronics", "Books", "Kitchen", "Toys", "Medical", "Other"]
    selected_categories = st.multiselect("Category", categories)
    
    # 2. Condition Select
    conditions = ["All", "New", "Like New", "Good", "Fair"]
    selected_condition = st.selectbox("Condition", conditions)
    
    # 3. City Text Filter
    city_filter = st.text_input("City", placeholder="e.g. Mumbai")
    
    # 4. Location Radius Filter
    st.subheader("Location radius")
    filter_by_location = st.checkbox("Filter by distance")
    
    lat_filter = None
    lng_filter = None
    radius_filter = 20
    
    if filter_by_location:
        lat_filter = st.number_input("Latitude", value=0.0, format="%.6f", min_value=-90.0, max_value=90.0)
        lng_filter = st.number_input("Longitude", value=0.0, format="%.6f", min_value=-180.0, max_value=180.0)
        radius_filter = st.slider("Radius (km)", 5, 100, 20)

# Build query params
params = {
    "status": "available",
    "page": 1,
    "page_size": 100  # Load all matching items for simplicity in MVP
}

if selected_categories:
    params["category"] = [c.lower() for c in selected_categories]
if selected_condition != "All":
    # Map "Like New" -> "like_new"
    cond_str = selected_condition.lower().replace(" ", "_")
    params["condition"] = cond_str
if city_filter:
    params["city"] = city_filter

if filter_by_location:
    if lat_filter != 0.0 or lng_filter != 0.0:
        params["lat"] = lat_filter
        params["lng"] = lng_filter
        params["radius_km"] = radius_filter
    else:
        st.sidebar.warning("Please enter non-zero coordinates to filter by distance.")

# Dialog for submitting request
@st.dialog("Request item")
def show_request_dialog(item_id, item_title):
    st.write(f"You are requesting: **{item_title}**")
    message = st.text_area("Message to donor", placeholder="Explain why you need this item or when you can pick it up...")
    
    ngo_note = None
    role = st.session_state.get("role")
    if role == "ngo":
        ngo_note = st.text_area("NGO note", placeholder="Explain the community impact or logistics details...")
    
    if st.button("Submit request", type="primary"):
        # NGO is allowed to send ngo_note, recipient gets blocked if they try (handled in backend but let's conform here)
        payload = {
            "item_id": item_id,
            "message": message if message else None
        }
        if role == "ngo" and ngo_note:
            payload["ngo_note"] = ngo_note
            
        try:
            api_client.post("/api/requests/", json=payload)
            st.success("Request submitted successfully!")
            st.rerun()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                st.error("Duplicate request: You already have a pending or active request for this item.")
            elif e.response.status_code == 400:
                st.error("Self-request: You cannot request your own item.")
            else:
                st.error(f"Failed to request item: {e.response.text}")
        except Exception as e:
            st.error(f"Error occurred: {str(e)}")

# Fetch and render items
try:
    response_data = api_client.get("/api/items/", params=params)
    items = response_data.get("items", [])
    
    if not items:
        st.info("No items found matching the selected filters.")
    else:
        # Display items in a grid layout (3 columns)
        cols = st.columns(3)
        for idx, item in enumerate(items):
            with cols[idx % 3]:
                # Donor cannot request their own item, and only recipient/ngo can request
                is_own_item = item.get("donor_id") == st.session_state.get("user_id")
                role_can_request = st.session_state.get("role") in ("recipient", "ngo")
                show_btn = role_can_request and not is_own_item
                
                # Callback trigger when clicking the request button
                def trigger_dialog(item_id=item["id"], title=item["title"]):
                    show_request_dialog(item_id, title)
                
                render_item_card(item, show_request_button=show_btn, on_request_click=trigger_dialog)
                
except Exception as e:
    st.error(f"Error loading items: {str(e)}")
