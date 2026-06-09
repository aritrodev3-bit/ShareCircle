# frontend/pages/6_NGO_Dashboard.py
import sys
import os
import streamlit as st
import httpx

# Ensure parent directory is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import api_client
from app import load_css, check_auth
from components.request_card import render_request_card

check_auth(allowed_roles=["ngo"])  # Navigation guard
load_css()

st.title("NGO Dashboard")

def handle_cancel(req_id):
    try:
        api_client.patch(f"/api/requests/{req_id}/cancel")
        st.toast("Request cancelled successfully.", icon="ℹ️")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to cancel request: {str(e)}")

try:
    # Fetch NGO's own requests
    ngo_requests = api_client.get("/api/requests/my")
    
    # Calculate metrics
    total_requested = len(ngo_requests)
    total_approved = len([r for r in ngo_requests if r.get("status") == "approved"])
    total_distributed = len([r for r in ngo_requests if r.get("status") == "picked_up"])
    
    # Display metric cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total requested items", total_requested)
    with col2:
        st.metric("Approved requests", total_approved)
    with col3:
        st.metric("Distributed to communities", total_distributed)
        
    st.write("")
    
    if not ngo_requests:
        st.info("You have not submitted any community requests yet. Go to 'Browse Items' to find and request available listings.")
    else:
        pending_requests = [r for r in ngo_requests if r.get("status") == "pending"]
        other_requests = [r for r in ngo_requests if r.get("status") != "pending"]
        
        tab_pending, tab_history = st.tabs(["Active requests", "Community allocation history"])
        
        with tab_pending:
            if not pending_requests:
                st.write("No active pending requests.")
            else:
                for req in pending_requests:
                    render_request_card(
                        req,
                        viewer_role="ngo",
                        on_cancel=handle_cancel
                    )
                    
        with tab_history:
            if not other_requests:
                st.write("No request history.")
            else:
                for req in other_requests:
                    render_request_card(
                        req,
                        viewer_role="ngo"
                    )
                    
except Exception as e:
    st.error(f"Error loading NGO requests: {str(e)}")
