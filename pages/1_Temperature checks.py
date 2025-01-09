import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from getNISEPdata import getTimeseries, getLookup
st.dataframe(st.session_state.df)
# --- Sidebar for Control ---
st.sidebar.title("Controls")

past_days_new = st.sidebar.number_input("Days Displayed", 1, None, st.session_state.past_days)

if past_days_new!=st.session_state.past_days:
    # --- Auth & Data Fetching ---
    auth_url = st.secrets.get("Login", {}).get("URL", "https://users.carnego.net")
    username = st.secrets.get("Login", {}).get("Username", "")
    password = st.secrets.get("Login", {}).get("Password", "")
    end_time = datetime(*datetime.now().timetuple()[:3])  # Today's date from the start of the day
    start_time = end_time - timedelta(days=past_days_new)  # Start time as per selected days
    st.session_state.df = getTimeseries(end_time, start_time, None, None, auth_url, username, password)
    st.session_state.past_days = past_days_new

# Retrieve the data from session state
temperature_columns = st.session_state.df.filter(like='Temperature').columns
columns_to_keep = ['datetime'] + list(temperature_columns)
# --- Main Content ---
st.title("📊 NISEP Time Series Data")
fig = px.line(st.session_state.df[columns_to_keep], x='datetime', y=columns_to_keep, title="Heat pump data over the past "+str(st.session_state.past_days)+" days")
st.plotly_chart(fig, use_container_width=True)
# --- Raw Data Preview ---
with st.expander("🗂️ Show Raw Data"):
    st.dataframe(st.session_state.df[columns_to_keep])  # Show last 10 rows of the data
