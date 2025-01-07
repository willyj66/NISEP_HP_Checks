import streamlit as st
from getNISEPdata import getTimeseries, getLookup
from datetime import datetime, timedelta
import plotly.express as px
import pandas as pd

# --- Auth & Data Fetching ---
auth_url = st.secrets.get("Login", {}).get("URL", "https://users.carnego.net")
username = st.secrets.get("Login", {}).get("Username", "")
password = st.secrets.get("Login", {}).get("Password", "")

# Cache Lookup Data
@st.cache_data
def cache_lookup():
    return getLookup(auth_url, username, password)

lookup_df = cache_lookup()
variables = lookup_df.name.unique()
sites = lookup_df.siteNamespace.unique()

# --- Sidebar for Control ---
st.sidebar.title("Controls")
site = st.sidebar.multiselect("Select Site", sites, sites[0])
variable = None # None for downloading all
past_days = st.sidebar.number_input("Days Displayed", 1, None, 1)

# Calculate start and end time
end_time = datetime(*datetime.now().timetuple()[:3])  # Get today's date from start of day
start_time = end_time - timedelta(days=past_days)  # Start time as per selected days
# Fetch the time series data
df = getTimeseries(end_time, start_time, site, variable, auth_url, username, password)

display_variable = st.sidebar.selectbox("Select Variable", df.columns[1:-1])  # Select a variable from the lookup
# --- Data Processing ---
if df.empty:
    st.warning("No data available for the selected parameters.")
else:
    df['datetime'] = pd.to_datetime(df['datetime'])  # Ensure 'datetime' is in proper format

    # --- Main Content ---
    st.title("📊 Time Series Data")

    # Plot using Plotly
    fig = px.line(df, x='datetime', y=variable, title="Time Series Data")
    st.plotly_chart(fig, use_container_width=True)

    # --- Quick Metrics Section ---
    latest_value = df[variable].iloc[-1] if not df.empty else "N/A"
    st.subheader("🔍 Quick Metrics")
    st.metric(label=f"Latest {variable}", value=latest_value)

    # --- Raw Data Preview ---
    with st.expander("🗂️ Show Raw Data"):
        st.dataframe(df.tail(10))  # Show last 10 rows of the data
