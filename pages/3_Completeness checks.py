import streamlit as st
import pandas as pd
from getNISEPdata import getTimeseries
from datetime import datetime, timedelta
st.set_page_config(layout="wide")

def calculate_missing_data_percentage(data):
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

# Fetch data for all intervals with None as columns argument
data_intervals = {
    "Daily": getTimeseries(end_time, end_time - timedelta(days=1), None, None, auth_url, username, password, interval="hour", averaging=averaging),
    "Weekly": getTimeseries(end_time, end_time - timedelta(days=7), None, None, auth_url, username, password, interval="hour", averaging=averaging),
    "Monthly": getTimeseries(end_time, end_time - timedelta(days=30), None, None, auth_url, username, password, interval="hour", averaging=averaging),
}

# --- Replace Zeros with None (NaN) ---
for interval, data in data_intervals.items():
    # Replace all zeros with NaN (None)
    data.replace(0, pd.NA, inplace=True)

# Store missing data percentages
missing_data_percentages = {}

# Calculate missing data percentages for each interval
for interval, data in data_intervals.items():
    missing_data_percentages[interval] = calculate_missing_data_percentage(data)

# --- Drop columns with all zeros ---
# Filter out columns with all zeros in the data
for interval, data in missing_data_percentages.items():
    non_zero_columns = {k: v for k, v in data.items() if not (data[k] == 0).all()}
    missing_data_percentages[interval] = non_zero_columns

# --- Round to one decimal place ---
for interval, data in missing_data_percentages.items():
    missing_data_percentages[interval] = {
        k: round(v, 1) for k, v in data.items()  # Round to one decimal place
    }
# --- Display Missing Data Percentages ---
st.title("📊 Missing Data Analysis")

st.write("Below are the missing data percentages for different time intervals:")

# Display the missing data percentages in a table
missing_data_df = pd.DataFrame(missing_data_percentages).T
st.dataframe(missing_data_df.replace(pd.NA, 0, inplace=True))

# --- Raw Data Preview ---
with st.expander("🗂️ Show Raw Data"):
    for interval, data in data_intervals.items():
        st.write(f"**{interval} Data**")
        st.dataframe(data)
