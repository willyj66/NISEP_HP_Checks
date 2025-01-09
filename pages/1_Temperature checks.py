import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from getNISEPdata import getTimeseries, getLookup

# Initialize session state variables if not already set
if 'past_days' not in st.session_state:
    st.session_state.past_days = 7  # Default to 7 days
if 'df' not in st.session_state:
    st.session_state.df = None
if 'df_temp' not in st.session_state:
    st.session_state.df_temp = None

# --- Sidebar for Control ---
st.sidebar.title("Controls")
past_days_new = st.sidebar.number_input("Days Displayed", 1, None, st.session_state.past_days)

# Fetch data only if the number of days changes
if past_days_new != st.session_state.past_days or st.session_state.df is None:
    # --- Auth & Data Fetching ---
    auth_url = st.secrets.get("Login", {}).get("URL", "https://users.carnego.net")
    username = st.secrets.get("Login", {}).get("Username", "")
    password = st.secrets.get("Login", {}).get("Password", "")
    end_time = datetime(*datetime.now().timetuple()[:3])  # Today's date from the start of the day
    start_time = end_time - timedelta(days=past_days_new)  # Start time as per selected days

    # Fetch new data and update session state
    st.session_state.df = getTimeseries(end_time, start_time, None, None, auth_url, username, password)
    st.session_state.past_days = past_days_new

    # Process and store temperature-related data
    df_sesh = st.session_state.df
    temperature_columns = df_sesh.filter(like='Temperature').columns
    columns_to_keep = ['datetime'] + list(temperature_columns)
    df_temp = df_sesh[columns_to_keep]
    df_temp['datetime'] = pd.to_datetime(df_temp['datetime'])  # Ensure 'datetime' is in proper format
    st.session_state.df_temp = df_temp

# Ensure processed data is available
if st.session_state.df_temp is not None:
    # --- Main Content ---
    st.title("📊 NISEP Time Series Data")
    fig = px.line(
        st.session_state.df_temp,
        x='datetime',
        y=st.session_state.df_temp.columns,
        title=f"Heat pump data over the past {st.session_state.past_days} days"
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Raw Data Preview ---
    with st.expander("🗂️ Show Raw Data"):
        st.dataframe(st.session_state.df_temp)  # Show raw data
else:
    st.error("No data available. Please adjust the number of days or check the data source.")
