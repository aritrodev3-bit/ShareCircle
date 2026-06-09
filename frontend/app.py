# frontend/app.py
import os
import streamlit as st

st.set_page_config(
    page_title="GiveCircle — Community Donation Platform",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "styles.css")
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# Navigation guard function
def check_auth(allowed_roles=None):
    if "token" not in st.session_state:
        st.warning("Please log in to access this page.")
        st.switch_page("pages/1_Login.py")
        st.stop()
    if allowed_roles and st.session_state.get("role") not in allowed_roles:
        st.error("You are not authorized to view this page.")
        st.switch_page("pages/3_Browse_Items.py")
        st.stop()

# Render main page logic
if __name__ == "__main__":
    st.title("GiveCircle")
    st.write("Welcome to GiveCircle, a platform connecting donors, recipients, and NGOs.")

    # Redirect to Browse if logged in, otherwise to Login
    if "token" in st.session_state:
        st.switch_page("pages/3_Browse_Items.py")
    else:
        st.switch_page("pages/1_Login.py")
