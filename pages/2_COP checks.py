import streamlit as st
import pandas as pd
from getNISEPdata import getTimeseries
from datetime import datetime, timedelta

# Function to calculate COP
def calculate_cop(data):
    df_numeric = data.drop(columns=['datetime'])
    cop = pd.DataFrame()

    for column in df_numeric.columns:
        if 'Output Heat Energy' in column:
            consumption_column = column.replace('Output Heat Energy', 'ASHP Consumption Energy')
            if consumption_column in df_numeric.columns:
                site_id = column.split('(')[-1].strip(')')  # Extract site ID
                cop.loc[site_id, 'COP'] = df_numeric[column].iloc[-1] / df_numeric[consumption_column].iloc[-1]

    return cop

# --- Sidebar for Control ---
st.sidebar.title("Controls")

st.sidebar.write("Select the time intervals to calculate the COP:")
past_days_new = st.sidebar.number_input("Days Displayed", 1, None, 30)

# --- Auth & Data Fetching ---
auth_url = st.secrets.get("Login", {}).get("URL", "https://users.carnego.net")
username = st.secrets.get("Login", {}).get("Username", "")
password = st.secrets.get("Login", {}).get("Password", "")

end_time = datetime(*datetime.now().timetuple()[:3])  # Today's date from the start of the day

# Fetch data for all intervals
data_intervals = {
    "Daily": getTimeseries(end_time, end_time - timedelta(days=1), None, ["ashp_c1_2_consumption_energy", "output_heat_energy"], auth_url, username, password, interval="hour"),
    "Weekly": getTimeseries(end_time, end_time - timedelta(days=7), None, ["ashp_c1_2_consumption_energy", "output_heat_energy"], auth_url, username, password, interval="hour"),
    "Monthly": getTimeseries(end_time, end_time - timedelta(days=30), None, ["ashp_c1_2_consumption_energy", "output_heat_energy"], auth_url, username, password, interval="day"),
}

cop_data = pd.DataFrame()

# Calculate COP for each interval
for interval, data in data_intervals.items():
    interval_cop = calculate_cop(data)
    interval_cop = interval_cop.rename(columns={"COP": interval})
    if cop_data.empty:
        cop_data = interval_cop
    else:
        cop_data = cop_data.merge(interval_cop, left_index=True, right_index=True, how="outer")

# Display COP Table
st.title("📊 Heat Pump COP Analysis")

st.write("Below is the COP analysis for different time intervals:")

st.dataframe(cop_data)

# --- Raw Data Preview ---
with st.expander("🗂️ Show Raw Data"):
    for interval, data in data_intervals.items():
        st.write(f"**{interval} Data**")
        st.dataframe(data)
