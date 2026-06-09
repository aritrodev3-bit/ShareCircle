# frontend/pages/1_Login.py
import sys
import os
import streamlit as st
import httpx

# Ensure parent directory is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import api_client
from app import load_css

load_css()

st.title("Sign in to GiveCircle")

with st.form("login_form"):
    email = st.text_input("Email address", placeholder="e.g. donor@givecircle.org")
    password = st.text_input("Password", type="password", placeholder="Enter your password")
    submitted = st.form_submit_button("Sign in", type="primary")

    if submitted:
        if not email or not password:
            st.error("Please enter both email and password.")
        else:
            try:
                # 1. Call login endpoint to get token
                login_data = api_client.login(email, password)
                token = login_data.get("access_token")
                
                # Store token temporarily in session state so get_me can use it
                st.session_state["token"] = token
                
                # 2. Call /me to get user details
                user_info = api_client.get("/api/auth/me")
                
                # 3. Store full session data
                st.session_state["user_id"] = user_info.get("id")
                st.session_state["role"] = user_info.get("role")
                st.session_state["full_name"] = user_info.get("full_name")
                st.session_state["email"] = user_info.get("email")
                
                st.success(f"Welcome back, {st.session_state['full_name']}!")
                st.switch_page("pages/3_Browse_Items.py")
            except httpx.HTTPStatusError as e:
                # Clear token if failed
                st.session_state.pop("token", None)
                if e.response.status_code == 401:
                    st.error("Invalid email or password.")
                else:
                    st.error(f"Login failed: {e.response.text}")
            except Exception as e:
                st.session_state.pop("token", None)
                st.error(f"An unexpected error occurred: {str(e)}")

# Registration redirect helper
st.write("New to GiveCircle?")
if st.button("Create an account"):
    st.switch_page("pages/2_Register.py")
