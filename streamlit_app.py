import streamlit as st
from getNISEPdata import getTimeseries, getLookup
from datetime import datetime, timedelta
import plotly.express as px
import pandas as pd

# Page layout configuration
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
all_variables = lookup_df.name.unique()
all_sites = lookup_df.siteNamespace.unique()

# --- Sidebar for Control ---
st.sidebar.title("Controls")
if 'past_days' not in st.session_state:
    past_days = st.sidebar.number_input("Days Displayed", 1, None, 1)
else:
    past_days = st.sidebar.number_input("Days Displayed", 1, None, st.session_state.past_days)
# Check if 'df' already exists in session state, otherwise fetch new data
if 'df' not in st.session_state or st.session_state.past_days != past_days:
    # Calculate start and end time
    end_time = datetime(*datetime.now().timetuple()[:3])  # Today's date from the start of the day
    start_time = end_time - timedelta(days=past_days)  # Start time as per selected days

    # Fetch the time series data and store it in session_state
    st.session_state.df = getTimeseries(end_time, start_time, None, None, auth_url, username, password)
    st.session_state.past_days = past_days  # Store the selected number of past days

# Retrieve the data from session state
df = st.session_state.df

# Sidebar site selection
display_site = st.sidebar.multiselect("Select Site", all_sites, all_sites)

# Filter available columns based on the selected sites
if display_site:
    site_columns = [
        col for col in df.columns if any(f"({site})" in col for site in display_site)
    ]
else:
    site_columns = df.columns[1:]  # Exclude 'datetime'

# Dynamically update the available variables based on the filtered columns
variable_options = list(set([
    col.split(" (")[0].strip() for col in site_columns
]))
display_variable = st.sidebar.multiselect("Select Variable", variable_options)

# Filter the dataframe to include only relevant columns
filtered_columns = ["datetime"] + [
    col for col in site_columns if col.split(" (")[0].strip() in display_variable
]

# --- Data Processing ---
if df.empty:
    st.warning("No data available for the selected parameters.")
else:
    # Ensure 'datetime' is in proper format
    df['datetime'] = pd.to_datetime(df['datetime'])

    # --- Main Content ---
    st.title("📊 NISEP Time Series Data")

    # Plotting multiple variables using Plotly
    if filtered_columns[1:]:
        fig = px.line(
            df,
            x='datetime',
            y=filtered_columns[1:],
            title=f"Heat pump data over the past {st.session_state.past_days} days"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Please select at least one variable to plot.")

    # --- Raw Data Preview ---
    with st.expander("🗂️ Show Raw Data"):
        st.dataframe(df[filtered_columns])  # Show filtered data for the selected columns
