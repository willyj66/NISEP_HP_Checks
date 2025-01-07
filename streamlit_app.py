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
variable = None  # None for downloading all
past_days = st.sidebar.number_input("Days Displayed", 1, None, 1)

# Check if 'df' already exists in session state, otherwise fetch new data
if 'df' not in st.session_state or st.session_state.site != site or st.session_state.past_days != past_days:
    # Calculate start and end time
    end_time = datetime(*datetime.now().timetuple()[:3])  # Get today's date from start of day
    start_time = end_time - timedelta(days=past_days)  # Start time as per selected days

    # Fetch the time series data and store it in session_state
    st.session_state.df = getTimeseries(end_time, start_time, site, variable, auth_url, username, password)
    st.session_state.site = site  # Store the selected site in session state
    st.session_state.past_days = past_days  # Store the selected number of past days

# Retrieve the data from session state
df = st.session_state.df

# Sidebar selection for variables to display
display_variable = st.sidebar.multiselect("Select Variable", df.columns[1:-1])  # Exclude 'datetime' and last column if it's not relevant

# --- Data Processing ---
if df.empty:
    st.warning("No data available for the selected parameters.")
else:
    df['datetime'] = pd.to_datetime(df['datetime'])  # Ensure 'datetime' is in proper format

    # --- Main Content ---
    st.title("📊 Time Series Data")

    # Plotting multiple variables using Plotly
    if display_variable:
        fig = px.line(df, x='datetime', y=display_variable, title="Time Series Data")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Please select at least one variable to plot.")

    # --- Quick Metrics Section ---
    if display_variable:
        st.subheader("🔍 Quick Metrics")
        for var in display_variable:
            mean_value = df[var].mean() if not df.empty else "N/A"
            st.metric(label=f"Average {var}", value=mean_value)

    # --- Raw Data Preview ---
    with st.expander("🗂️ Show Raw Data"):
        st.dataframe(df)  # Show last 10 rows of the data
