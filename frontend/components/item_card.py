# frontend/components/item_card.py
import streamlit as st
from components.status_badge import status_badge, category_badge

def render_item_card(item: dict, show_request_button: bool, on_request_click=None):
    html = f"""
    <div style="
        background-color: #1F2211;
        border: 0.5px solid rgba(167,209,41,0.08);
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 12px;
        transition: background-color 150ms ease;
    ">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
            <span style="font-size:15px; font-weight:500; color:#E8EDE0;">{item['title']}</span>
            {status_badge(item['status'])}
        </div>
        <div style="margin-bottom:6px;">
            {category_badge(item['category'])}
        </div>
        <p style="font-size:14px; color:#9AA582; margin:6px 0;">{item['description'][:120]}{'...' if len(item['description']) > 120 else ''}</p>
        <div style="display:flex; gap:12px; font-size:12px; color:#616B4E; margin-top:8px;">
            <span>📍 {item['city']}</span>
            <span>Condition: {item['condition'].replace('_', ' ').title()}</span>
            <span>Qty: {item['quantity']}</span>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    if show_request_button and on_request_click:
        if st.button("Request This Item", key=f"req_{item['id']}"):
            on_request_click(item["id"])
