# frontend/pages/7_Analytics.py
import sys
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import httpx

# Ensure parent directory is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import api_client
from app import load_css, check_auth
from chart_theme import apply_theme

check_auth(allowed_roles=["admin"])  # Navigation guard
load_css()

st.title("Platform analytics")

try:
    # 1. Fetch summary metrics
    summary = api_client.get("/api/analytics/summary")
    
    # Display metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total donors", summary.get("total_donors", 0))
    with col2:
        st.metric("Total recipients", summary.get("total_recipients", 0))
    with col3:
        st.metric("Items donated", summary.get("total_items_donated", 0))
    with col4:
        st.metric("People helped", summary.get("people_helped", 0))
        
    st.write("")
    
    # 2x2 Grid of charts
    row1_col1, row1_col2 = st.columns(2)
    row2_col1, row2_col2 = st.columns(2)
    
    # Chart 1: Category breakdown of donated items
    with row1_col1:
        try:
            cat_data = api_client.get("/api/analytics/category-breakdown")
            df_cat = pd.DataFrame(cat_data)
            if not df_cat.empty:
                df_cat["category"] = df_cat["category"].str.capitalize()
                fig_cat = px.bar(
                    df_cat,
                    x="category",
                    y="count",
                    labels={"category": "Category", "count": "Donated items"},
                    title="Donated items by category"
                )
                fig_cat = apply_theme(fig_cat)
                st.plotly_chart(fig_cat, use_container_width=True)
            else:
                st.info("No category breakdown data available yet.")
        except Exception as e:
            st.error(f"Error loading category breakdown: {str(e)}")
            
    # Chart 2: Donation trend over last 30 days
    with row1_col2:
        try:
            trend_data = api_client.get("/api/analytics/donation-trend")
            df_trend = pd.DataFrame(trend_data)
            if not df_trend.empty:
                fig_trend = px.line(
                    df_trend,
                    x="date",
                    y="count",
                    labels={"date": "Date", "count": "Donated items"},
                    title="Donation trend (last 30 days)"
                )
                fig_trend = apply_theme(fig_trend)
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("No donation trend data available yet.")
        except Exception as e:
            st.error(f"Error loading donation trend: {str(e)}")
            
    # Chart 3: Top 10 cities by item listings
    with row2_col1:
        try:
            city_data = api_client.get("/api/analytics/top-cities")
            df_city = pd.DataFrame(city_data)
            if not df_city.empty:
                fig_city = px.bar(
                    df_city,
                    x="city",
                    y="count",
                    labels={"city": "City", "count": "Listings"},
                    title="Top cities by listings"
                )
                fig_city = apply_theme(fig_city)
                st.plotly_chart(fig_city, use_container_width=True)
            else:
                st.info("No city listings data available yet.")
        except Exception as e:
            st.error(f"Error loading city listings: {str(e)}")
            
    # Chart 4: Platform activity (daily new users, items, requests)
    with row2_col2:
        try:
            activity_data = api_client.get("/api/analytics/platform-activity")
            df_activity = pd.DataFrame(activity_data)
            if not df_activity.empty:
                df_melt = df_activity.melt(
                    id_vars=["date"],
                    value_vars=["new_users", "new_items", "new_requests"],
                    var_name="activity_type",
                    value_name="count"
                )
                df_melt["activity_type"] = df_melt["activity_type"].str.replace("new_", "").str.capitalize()
                fig_activity = px.bar(
                    df_melt,
                    x="date",
                    y="count",
                    color="activity_type",
                    barmode="group",
                    labels={"date": "Date", "count": "Count", "activity_type": "Activity type"},
                    title="Platform activity (last 30 days)"
                )
                fig_activity = apply_theme(fig_activity)
                st.plotly_chart(fig_activity, use_container_width=True)
            else:
                st.info("No platform activity data available yet.")
        except Exception as e:
            st.error(f"Error loading platform activity: {str(e)}")

except httpx.HTTPStatusError as e:
    if e.response.status_code == 403:
        st.error("Access denied. Admin role required.")
    else:
        st.error(f"Failed to load analytics: {e.response.text}")
except Exception as e:
    st.error(f"An unexpected error occurred: {str(e)}")
