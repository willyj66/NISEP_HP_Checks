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
sites = lookup_df.siteNamespace.unique()

# --- Sidebar for Control ---
st.sidebar.title("Controls")
site = None  # None for downloading all
variable = None  # None for downloading all
past_days = st.sidebar.number_input("Days Displayed", 1, None, 1)

display_site = st.sidebar.multiselect("Select Site for Visualization", sites)

def filter_df(df, display_site):
    if display_site:
        return df[df['siteNamespace'].isin(display_site)]
    return df

# Check if 'df' already exists in session state, otherwise fetch new data
if 'df' not in st.session_state or st.session_state.site != site or st.session_state.past_days != past_days:
    # Calculate start and end time
    end_time = datetime(*datetime.now().timetuple()[:3])  # Get today's date from start of day
    start_time = end_time - timedelta(days=past_days)  # Start time as per selected days

    # Fetch the time series data and store it in session_state
    st.session_state.df = getTimeseries(end_time, start_time, site, variable, auth_url, username, password)
    st.session_state.past_days = past_days  # Store the selected number of past days

# Retrieve the data from session state
df = st.session_state.df

# Sidebar selection for variables to display
display_variable = st.sidebar.multiselect("Select Variable", df.columns[1:])  # Exclude 'datetime' and last column if it's not relevant

# --- Data Processing ---
if df.empty:
    st.warning("No data available for the selected parameters.")
else:
    df['datetime'] = pd.to_datetime(df['datetime'])  # Ensure 'datetime' is in proper format

    # Filter the data for visualization based on selected sites
    filtered_df = filter_df(df, display_site)

    # --- Main Content ---
    st.title("NISEP Time Series Data")

    # Plotting multiple variables using Plotly
    if display_variable:
        fig = px.line(filtered_df, x='datetime', y=display_variable, title="Heat pump data over the past " + str(st.session_state.past_days) + " days")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Please select at least one variable to plot.")

    # --- Quick Metrics Section ---
    if display_variable:
        st.subheader("\ud83d\udd0d Quick Metrics")
        for var in display_variable:
            mean_value = filtered_df[var].mean() if not filtered_df.empty else "N/A"
            st.metric(label=f"Average {var}", value=mean_value)

    # --- Raw Data Preview ---
    with st.expander("\ud83d\uddc2\ufe0f Show Raw Data"):
        st.dataframe(filtered_df)  # Show last 10 rows of the data
