# frontend/pages/5_My_Requests.py
import sys
import os
import streamlit as st
import httpx

# Ensure parent directory is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import api_client
from app import load_css, check_auth
from components.request_card import render_request_card

check_auth(allowed_roles=["recipient"])  # Navigation guard
load_css()

st.title("My requests")

def handle_cancel(req_id):
    try:
        api_client.patch(f"/api/requests/{req_id}/cancel")
        st.toast("Request cancelled successfully.", icon="ℹ️")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to cancel request: {str(e)}")

try:
    my_requests = api_client.get("/api/requests/my")
    
    if not my_requests:
        st.info("You have not submitted any requests yet.")
    else:
        # Separate pending and past requests for cleaner UI
        pending_requests = [r for r in my_requests if r.get("status") == "pending"]
        other_requests = [r for r in my_requests if r.get("status") != "pending"]
        
        tab_pending, tab_history = st.tabs(["Active requests", "Request history"])
        
        with tab_pending:
            if not pending_requests:
                st.write("No active pending requests.")
            else:
                for req in pending_requests:
                    render_request_card(
                        req,
                        viewer_role="recipient",
                        on_cancel=handle_cancel
                    )
                    
        with tab_history:
            if not other_requests:
                st.write("No request history.")
            else:
                for req in other_requests:
                    render_request_card(
                        req,
                        viewer_role="recipient"
                    )
                    
except Exception as e:
    st.error(f"Error loading requests: {str(e)}")
