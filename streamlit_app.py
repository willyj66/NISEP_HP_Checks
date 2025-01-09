import streamlit as st
from getNISEPdata import getTimeseries, getLookup
from datetime import datetime, timedelta
import plotly.express as px
import pandas as pd
st.set_page_config(layout="wide")
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
st.session_state.sites = lookup_df.siteNamespace.unique()
sites = st.session_state.sites

# --- Sidebar for Control ---
st.sidebar.title("Controls")
site = None #None for downloading all
variable = None  # None for downloading all
past_days = st.sidebar.number_input("Days Displayed", 1, None, 1)

# Check if 'df' already exists in session state, otherwise fetch new data
if 'df' not in st.session_state or st.session_state.past_days != past_days:
    # Calculate start and end time
    end_time = datetime(*datetime.now().timetuple()[:3])  # Get today's date from start of day
    start_time = end_time - timedelta(days=past_days)  # Start time as per selected days

    # Fetch the time series data and store it in session_state
    st.session_state.df = getTimeseries(end_time, start_time, site, variable, auth_url, username, password)
    #st.session_state.site = site  # Store the selected site in session state
    st.session_state.past_days = past_days  # Store the selected number of past days

# Retrieve the data from session state
df = st.session_state.df

# Sidebar selection for variables to display
display_variable = st.sidebar.multiselect("Select Variable", df.columns[1:])  # Exclude 'datetime' and last column if it's not relevant
display_site = st.sidebar.multiselect("Select Site", sites,sites)
# Filter columns based on selected sites
if display_site:
    site_columns = [
        col for col in df.columns
        if any(f"({site})" in col for site in display_site)
    ]
else:
    site_columns = []
# --- Data Processing ---
if df.empty:
    st.warning("No data available for the selected parameters.")
else:
    # Ensure 'datetime' is in proper format
    df['datetime'] = pd.to_datetime(df['datetime'])

    # --- Main Content ---
    st.title("📊 NISEP Time Series Data")

    # Plotting multiple variables using Plotly
    if site_columns:
        fig = px.line(
            df,
            x='datetime',
            y=site_columns,
            title=f"Heat pump data over the past {st.session_state.past_days} days"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Please select at least one site to plot.")

    # --- Raw Data Preview ---
    with st.expander("🗂️ Show Raw Data"):
        st.dataframe(df[['datetime'] + site_columns])  # Show data for the selected site columns