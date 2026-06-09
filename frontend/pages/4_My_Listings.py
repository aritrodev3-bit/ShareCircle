# frontend/pages/4_My_Listings.py
import sys
import os
import streamlit as st
import httpx

# Ensure parent directory is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import api_client
from app import load_css, check_auth
from components.item_card import render_item_card
from components.request_card import render_request_card

check_auth(allowed_roles=["donor"])  # Navigation guard
load_css()

st.title("My listings")

# Action Callbacks
def handle_approve(req_id):
    try:
        api_client.patch(f"/api/requests/{req_id}/approve")
        st.toast("Request approved successfully!", icon="✅")
        st.rerun()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            st.error("Conflict: This item has already been reserved or approved for another request.")
        else:
            st.error(f"Failed to approve request: {e.response.text}")

def handle_reject(req_id):
    try:
        api_client.patch(f"/api/requests/{req_id}/reject")
        st.toast("Request rejected.", icon="ℹ️")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to reject request: {str(e)}")

def handle_pickup(req_id):
    try:
        api_client.patch(f"/api/requests/{req_id}/pickup")
        st.toast("Pickup confirmed. Item marked as donated!", icon="🎉")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to confirm pickup: {str(e)}")

def handle_delete_item(item_id):
    try:
        api_client.delete(f"/api/items/{item_id}")
        st.toast("Listing removed successfully.", icon="🗑️")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to remove listing: {str(e)}")

# Add New Listing expander
with st.expander("Add new listing", expanded=False):
    with st.form("add_listing_form"):
        title = st.text_input("Title", placeholder="e.g. Wooden Dining Table")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            category_options = ["Clothing", "Furniture", "Electronics", "Books", "Kitchen", "Toys", "Medical", "Other"]
            category = st.selectbox("Category", category_options)
        with col2:
            condition_options = ["New", "Like New", "Good", "Fair"]
            condition = st.selectbox("Condition", condition_options)
        with col3:
            quantity = st.number_input("Quantity", min_value=1, value=1)
            
        description = st.text_area("Description", placeholder="Describe the item, its size, wear and tear, and pickup availability...")
        
        col_city, col_pin = st.columns(2)
        with col_city:
            city = st.text_input("City", placeholder="e.g. Mumbai")
        with col_pin:
            pincode = st.text_input("Pincode", placeholder="e.g. 400001")
            
        image_url = st.text_input("Image URL (optional)", placeholder="e.g. https://example.com/image.jpg")
        
        # Location Coordinates
        st.subheader("Coordinates (optional, for radius search)")
        add_coordinates = st.checkbox("Specify exact coordinates")
        lat = None
        lng = None
        if add_coordinates:
            col_lat, col_lng = st.columns(2)
            with col_lat:
                lat = st.number_input("Latitude", value=0.0, format="%.6f", min_value=-90.0, max_value=90.0)
            with col_lng:
                lng = st.number_input("Longitude", value=0.0, format="%.6f", min_value=-180.0, max_value=180.0)
                
        submitted = st.form_submit_button("Submit listing", type="primary")
        
        if submitted:
            if not title or not description or not city or not pincode:
                st.error("Please fill in all required fields (Title, Description, City, and Pincode).")
            else:
                try:
                    payload = {
                        "title": title,
                        "description": description,
                        "category": category.lower(),
                        "condition": condition.lower().replace(" ", "_"),
                        "quantity": quantity,
                        "city": city,
                        "pincode": pincode,
                        "image_url": image_url if image_url else None,
                        "lat": lat if add_coordinates else None,
                        "lng": lng if add_coordinates else None
                    }
                    api_client.post("/api/items/", json=payload)
                    st.success("Listing created successfully!")
                    st.rerun()
                except httpx.HTTPStatusError as e:
                    st.error(f"Failed to create listing: {e.response.text}")
                except Exception as e:
                    st.error(f"Error occurred: {str(e)}")

# Fetch incoming requests to display under listings
try:
    incoming_requests = api_client.get("/api/requests/incoming")
except Exception as e:
    incoming_requests = []
    st.error(f"Error loading incoming requests: {str(e)}")

# Set up tabs for different listing states
tab_available, tab_reserved, tab_completed, tab_removed = st.tabs([
    "Available", "Reserved", "Completed", "Removed"
])

def render_listings_tab(status_value):
    try:
        response_data = api_client.get("/api/items/", params={"mine": "true", "status": status_value})
        my_items = response_data.get("items", [])
        
        if not my_items:
            st.info(f"You have no listings in the '{status_value}' state.")
            return

        for item in my_items:
            # Match requests for this item
            item_requests = [r for r in incoming_requests if r.get("item_id") == item["id"]]
            
            # Create a box container for each listing
            with st.container():
                st.markdown("---")
                # Grid for listing card and details
                render_item_card(item, show_request_button=False)
                
                # Delete/remove button (only for available items)
                if status_value == "available":
                    if st.button("Remove listing", key=f"del_{item['id']}", type="secondary"):
                        handle_delete_item(item["id"])
                
                # Render incoming requests
                if item_requests:
                    with st.expander(f"Incoming requests ({len(item_requests)})"):
                        for req in item_requests:
                            render_request_card(
                                req,
                                viewer_role="donor",
                                on_approve=handle_approve,
                                on_reject=handle_reject,
                                on_pickup=handle_pickup
                            )
                else:
                    if status_value == "available":
                        st.caption("No incoming requests for this item yet.")
                        
    except Exception as e:
        st.error(f"Error loading listings: {str(e)}")

with tab_available:
    render_listings_tab("available")
with tab_reserved:
    render_listings_tab("reserved")
with tab_completed:
    render_listings_tab("donated")
with tab_removed:
    render_listings_tab("removed")
