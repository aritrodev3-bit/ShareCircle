# frontend/pages/2_Register.py
import sys
import os
import streamlit as st
import httpx

# Ensure parent directory is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import api_client
from app import load_css

load_css()

st.title("Create your GiveCircle account")

with st.form("register_form"):
    full_name = st.text_input("Full name", placeholder="e.g. Jane Doe")
    email = st.text_input("Email address", placeholder="e.g. jane.doe@example.com")
    password = st.text_input("Password", type="password", help="Password must be at least 8 characters long.")
    role = st.selectbox("I want to register as a", ["Donor", "Recipient", "NGO"])
    phone = st.text_input("Phone number (optional)", placeholder="e.g. +1234567890")
    
    submitted = st.form_submit_button("Register", type="primary")

    if submitted:
        # Client side checks
        if not full_name or not email or not password:
            st.error("Please fill in all required fields (Full name, Email, and Password).")
        elif len(password) < 8:
            st.error("Password must be at least 8 characters long.")
        else:
            try:
                # Map selectbox string to UserRole enum values: "donor", "recipient", "ngo"
                role_map = {
                    "Donor": "donor",
                    "Recipient": "recipient",
                    "NGO": "ngo"
                }
                api_role = role_map[role]
                
                # 1. POST registration payload
                payload = {
                    "email": email,
                    "password": password,
                    "full_name": full_name,
                    "role": api_role,
                    "phone": phone if phone else None
                }
                api_client.post("/api/auth/register", json=payload)
                
                # 2. Auto-login on success
                login_data = api_client.login(email, password)
                token = login_data.get("access_token")
                
                # Store session details
                st.session_state["token"] = token
                
                user_info = api_client.get("/api/auth/me")
                st.session_state["user_id"] = user_info.get("id")
                st.session_state["role"] = user_info.get("role")
                st.session_state["full_name"] = user_info.get("full_name")
                st.session_state["email"] = user_info.get("email")
                
                st.success("Registration successful! Logging you in...")
                st.switch_page("pages/3_Browse_Items.py")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 400:
                    st.error("An account with this email address already exists.")
                elif e.response.status_code == 422:
                    st.error("Invalid email address format or inputs.")
                else:
                    st.error(f"Registration failed: {e.response.text}")
            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")

# Login redirect helper
st.write("Already have an account?")
if st.button("Sign in"):
    st.switch_page("pages/1_Login.py")
