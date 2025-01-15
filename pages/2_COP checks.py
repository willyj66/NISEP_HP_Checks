import streamlit as st
import pandas as pd
from getNISEPdata import getTimeseries
from datetime import datetime, timedelta

def calculate_cop(data):
    df_numeric = data.drop(columns=['datetime'])
    cop = pd.DataFrame()
    heat_diff = pd.DataFrame()
    consumption_diff = pd.DataFrame()

    for column in df_numeric.columns:
        if 'Output Heat Energy' in column:
            consumption_column = column.replace('Output Heat Energy', 'ASHP Consumption Energy')
            if consumption_column in df_numeric.columns:
                site_id = column.split('(')[-1].strip(')')  # Extract site ID

                # Compute differences
                heat_diff.loc[site_id, 'Heat Diff'] = df_numeric[column].iloc[-1] - df_numeric[column].iloc[0]
                consumption_diff.loc[site_id, 'Consumption Diff'] = df_numeric[consumption_column].iloc[-1] - df_numeric[consumption_column].iloc[0]

                # Calculate COP
                cop.loc[site_id, 'COP'] = heat_diff.loc[site_id, 'Heat Diff'] / consumption_diff.loc[site_id, 'Consumption Diff']

    return cop, heat_diff, consumption_diff

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
    "Daily": getTimeseries(end_time, end_time - timedelta(days=1), None, ["ashp_c1_2_consumption_energy", "output_heat_energy"], auth_url, username, password, interval="hour", averaging=averaging),
    "Weekly": getTimeseries(end_time, end_time - timedelta(days=7), None, ["ashp_c1_2_consumption_energy", "output_heat_energy"], auth_url, username, password, interval="hour", averaging=averaging),
    "Monthly": getTimeseries(end_time, end_time - timedelta(days=30), None, ["ashp_c1_2_consumption_energy", "output_heat_energy"], auth_url, username, password, interval="day", averaging=averaging),
}

cop_data = pd.DataFrame()
heat_diff_data = pd.DataFrame()
consumption_diff_data = pd.DataFrame()

# Calculate COP, heat diff, and consumption diff for each interval
for interval, data in data_intervals.items():
    interval_cop, interval_heat_diff, interval_consumption_diff = calculate_cop(data)
    interval_cop = interval_cop.rename(columns={"COP": interval})
    interval_heat_diff = interval_heat_diff.rename(columns={"Heat Diff": interval})
    interval_consumption_diff = interval_consumption_diff.rename(columns={"Consumption Diff": interval})

    # Merge data for display
    if cop_data.empty:
        cop_data = interval_cop
        heat_diff_data = interval_heat_diff
        consumption_diff_data = interval_consumption_diff
    else:
        cop_data = cop_data.merge(interval_cop, left_index=True, right_index=True, how="outer")
        heat_diff_data = heat_diff_data.merge(interval_heat_diff, left_index=True, right_index=True, how="outer")
        consumption_diff_data = consumption_diff_data.merge(interval_consumption_diff, left_index=True, right_index=True, how="outer")

# Display COP Table
st.title("📊 Heat Pump COP Analysis")

st.write("Below is the COP analysis for different time intervals:")

st.dataframe(cop_data)

# Display Heat Diff Table
st.write("Below is the Heat Energy Difference analysis for different time intervals:")

st.dataframe(heat_diff_data)

# Display Consumption Diff Table
st.write("Below is the Consumption Energy Difference analysis for different time intervals:")

st.dataframe(consumption_diff_data)

# --- Raw Data Preview ---
with st.expander("🗂️ Show Raw Data"):
    for interval, data in data_intervals.items():
        st.write(f"**{interval} Data**")
        st.dataframe(data)
