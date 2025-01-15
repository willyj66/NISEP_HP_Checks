import streamlit as st
import pandas as pd
from getNISEPdata import getTimeseries
from datetime import datetime, timedelta

# --- Sidebar for Date Selection ---
st.sidebar.title("COP Analysis Settings")

# Select date ranges
analysis_range = st.sidebar.radio(
    "Select Analysis Range:",
    ["Daily", "Weekly", "Monthly"],
    index=2
)

# Mapping ranges to days
range_mapping = {
    "Daily": 1,
    "Weekly": 7,
    "Monthly": 30
}

selected_days = range_mapping[analysis_range]

# Retrieve login credentials from Streamlit secrets
url = st.secrets.get("Login", {}).get("URL", "https://users.carnego.net")
username = st.secrets.get("Login", {}).get("Username", "")
password = st.secrets.get("Login", {}).get("Password", "")

# Define variables for the heat pump analysis
variables = ["ashp_c1_2_consumption_energy", "output_heat_energy"]

# Fetch the data based on selected range
end_time = datetime(*datetime.now().timetuple()[:3])
start_time = end_time - timedelta(days=selected_days)
data = getTimeseries(end_time, start_time, None, variables, url, username, password, interval="hour" if selected_days == 30 else "day")

# Extract numeric data for calculations
df_numeric = data.drop(columns=['datetime'])

# Calculate differences between the last and first rows (for cumulative energy)
difference = df_numeric.iloc[-1] - df_numeric.iloc[0]

# Create an empty Series to store COP values
cop = pd.Series(dtype='float64')

# Calculate COP for each Output Heat Energy and corresponding ASHP Consumption Energy column
for column in df_numeric.columns:
    if 'Output Heat Energy' in column:  # Find Output Heat Energy columns
        # Get the corresponding ASHP Consumption Energy column
        consumption_column = column.replace('Output Heat Energy', 'ASHP Consumption Energy')

        # Calculate COP if both columns exist
        if consumption_column in df_numeric.columns:
            cop[column] = df_numeric[column].iloc[-1] / df_numeric[consumption_column].iloc[-1]

# --- Main Content ---
st.title("Coefficient of Performance (COP) Analysis")

# Display the analysis range and results
st.subheader(f"Analysis Range: {analysis_range}")

if cop.empty:
    st.warning("No COP data available for the selected range.")
else:
    st.success("COP calculated successfully!")
    
    # Display the COP values in a table
    st.write("### COP Values")
    st.table(cop.reset_index().rename(columns={"index": "Heat Pump", 0: "COP Value"}))

    # Highlight any COP values below a threshold (e.g., 2.5)
    low_cop_threshold = 2.5
    low_cop = cop[cop < low_cop_threshold]

    if not low_cop.empty:
        st.warning(f"The following heat pumps have COP below {low_cop_threshold}:")
        st.table(low_cop.reset_index().rename(columns={"index": "Heat Pump", 0: "COP Value"}))

# --- Raw Data Display ---
with st.expander("🗂️ Show Raw Data"):
    st.dataframe(data)
