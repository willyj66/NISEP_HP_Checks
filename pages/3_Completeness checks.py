import streamlit as st
import pandas as pd
import re  # Import regex
from getNISEPdata import getTimeseries
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

def calculate_missing_data_percentage(data):
    """Calculate percentage of missing data for each column in the dataframe."""
    missing_data_percentage = {}
    for column in data.columns:
        missing_count = data[column].isna().sum()
        total_count = len(data[column])
        missing_data_percentage[column] = (missing_count / total_count) * 100
    return missing_data_percentage

# --- Sidebar for Control ---
st.sidebar.title("Controls")
averaging = st.sidebar.selectbox("Averaging Type", ['max', 'min', 'average'])

# --- Auth & Data Fetching ---
auth_url = st.secrets.get("Login", {}).get("URL", "https://users.carnego.net")
username = st.secrets.get("Login", {}).get("Username", "")
password = st.secrets.get("Login", {}).get("Password", "")

end_time = datetime(*datetime.now().timetuple()[:3])  # Today's date from the start of the day

# Fetch data for all intervals
data_intervals = {
    "Daily": getTimeseries(end_time, end_time - timedelta(days=1), None, None, auth_url, username, password, interval="hour", averaging=averaging),
    "Weekly": getTimeseries(end_time, end_time - timedelta(days=7), None, None, auth_url, username, password, interval="hour", averaging=averaging),
    "Monthly": getTimeseries(end_time, end_time - timedelta(days=30), None, None, auth_url, username, password, interval="hour", averaging=averaging),
}

# --- Replace Zeros with NaN (None) ---
for interval, data in data_intervals.items():
    data.replace(0, pd.NA, inplace=True)

# Store missing data percentages
missing_data_percentages = {}

# Calculate missing data percentages for each interval
for interval, data in data_intervals.items():
    missing_data_percentages[interval] = calculate_missing_data_percentage(data)

# Convert to DataFrame
missing_data_df = pd.DataFrame(missing_data_percentages).fillna(value=0)

# --- Split Data by Site (Fix Site Detection) ---
site_groups = {}

for row_name in missing_data_df.index:
    match = re.search(r"\((NISEP\d{2})\)", row_name)  # Extracts only NISEPXX format
    if match:
        site_id = match.group(1)  # Correctly extracts "NISEP01", "NISEP02", etc.
        if site_id not in site_groups:
            site_groups[site_id] = {}
        site_groups[site_id][row_name] = missing_data_df.loc[row_name]

# Convert to DataFrames
for site_id, site_data in site_groups.items():
    site_groups[site_id] = pd.DataFrame(site_data).T  # Transpose for better readability
    site_groups[site_id] = site_groups[site_id].loc[~(site_groups[site_id].eq(0).all(axis=1))]

# --- Highlight Values > 30 in Red ---
def highlight_high_values(val):
    """Highlight values greater than 30 in red."""
    return 'background-color: red' if val > 30 else ''

# --- Display Data ---
st.title("📊 Missing Data Analysis by Site")

for site_id, df in site_groups.items():
    st.subheader(f"📍 Site: {site_id}")
    st.dataframe(df.style.applymap(highlight_high_values))
