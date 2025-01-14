import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from getNISEPdata import getTimeseries

# --- Sidebar for Control ---
st.sidebar.title("Controls")

past_days_new = st.sidebar.number_input("Days Displayed", 1, None, st.session_state.past_days)

# Updated default boundary settings
default_boundaries = {
    "Flow/Return": {"min": 10, "max": 70},
    "Outdoor": {"min": -10, "max": 30},
    "Indoor": {"min": 15, "max": 26},
}

# Sidebar expander for range adjustments
with st.sidebar.expander("Adjust Boundaries"):
    flow_min = st.number_input("Flow/Return Min", value=default_boundaries["Flow/Return"]["min"])
    flow_max = st.number_input("Flow/Return Max", value=default_boundaries["Flow/Return"]["max"])
    outdoor_min = st.number_input("Outdoor Min", value=default_boundaries["Outdoor"]["min"])
    outdoor_max = st.number_input("Outdoor Max", value=default_boundaries["Outdoor"]["max"])
    indoor_min = st.number_input("Indoor Min", value=default_boundaries["Indoor"]["min"])
    indoor_max = st.number_input("Indoor Max", value=default_boundaries["Indoor"]["max"])

if past_days_new != st.session_state.past_days:
    # --- Auth & Data Fetching ---
    auth_url = st.secrets.get("Login", {}).get("URL", "https://users.carnego.net")
    username = st.secrets.get("Login", {}).get("Username", "")
    password = st.secrets.get("Login", {}).get("Password", "")
    end_time = datetime(*datetime.now().timetuple()[:3])  # Today's date from the start of the day
    start_time = end_time - timedelta(days=past_days_new)  # Start time as per selected days
    st.session_state.df = getTimeseries(end_time, start_time, None, None, auth_url, username, password)
    st.session_state.past_days = past_days_new

# Retrieve the data from session state
df_sesh = st.session_state.df
temperature_columns = df_sesh.filter(like='Temperature').columns

# Dynamically update the available variables based on the filtered columns
variable_options = list(set([
    col.split(" (")[0].strip() for col in temperature_columns
]))

# Function to determine min/max values based on variable type
def get_conditions(variable):
    if "Flow" in variable or "Return" in variable:
        return {"min": flow_min, "max": flow_max}
    elif "Outdoor" in variable:
        return {"min": outdoor_min, "max": outdoor_max}
    else:
        return {"min": indoor_min, "max": indoor_max}

# Extract location IDs from variable names
def extract_location(variable_name):
    if "(" in variable_name and ")" in variable_name:
        return variable_name.split("(")[-1].strip(")")
    return "Unknown"

# --- Main Content ---
st.title("📊 NISEP Time Series Data")

for variable in variable_options:
    # Filter columns corresponding to the current variable
    relevant_columns = [col for col in temperature_columns if col.startswith(variable)]
    if not relevant_columns:
        continue
    if variable=="Temperature":

    # Prepare the data
    df = df_sesh[["datetime"] + relevant_columns]
    df['datetime'] = pd.to_datetime(df['datetime'])

    # Get conditions for the current variable
    conditions = get_conditions(variable)

    # Extract location IDs
    locations = {col: extract_location(col) for col in relevant_columns}

    # Determine locations with out-of-range data
    out_of_range_locations = [
        col for col in relevant_columns
        if ((df[col] < conditions["min"]) | (df[col] > conditions["max"])).any()
    ]

    if not out_of_range_locations:
        continue  # Skip if no out-of-range data

    # Horizontal checkboxes for filtering locations, using multiple columns
    st.write(f"**Select Locations for {variable}**:")
    selected_locations = []
    
    # Determine how many columns to create (e.g., 3 columns if there are 6 locations)
    num_columns = len(out_of_range_locations)
    columns = st.columns(num_columns)  # Create the columns dynamically
    
    # Create a checkbox for each location across the columns
    for idx, col in enumerate(out_of_range_locations):
        location_id = locations[col]
        with columns[idx % num_columns]:  # Distribute checkboxes across columns
            if st.checkbox(location_id, value=True, key=f"checkbox_{variable}_{location_id}"):
                selected_locations.append(col)

    # Create the plot
    fig = go.Figure()
    for column in relevant_columns:
        # Skip if the location is not selected
        if column not in selected_locations:
            continue

        # Identify in-range and out-of-range data
        out_of_range_mask = (df[column] < conditions["min"]) | (df[column] > conditions["max"])
        in_range_mask = ~out_of_range_mask

        # Add in-range data (hidden in legend)
        fig.add_trace(go.Scatter(
            x=df["datetime"],
            y=df[column].where(in_range_mask),
            mode="lines",
            name=f"In-Range: {locations[column]}",
            line=dict(width=2, color="blue"),
            showlegend=False  # Hide in-range traces from the legend
        ))

        # Add out-of-range data
        fig.add_trace(go.Scatter(
            x=df["datetime"],
            y=df[column].where(out_of_range_mask),
            mode="lines",
            name=f"{variable} ({locations[column]})",
            line=dict(width=3, color="red"),
        ))

    fig.update_layout(
        title=f"{variable} Data",
        xaxis_title="Datetime",
        yaxis_title="Temperature (°C)",
        legend_title="Out-of-Range Locations",
        template="plotly_white",
    )

    st.plotly_chart(fig, use_container_width=True)

# --- Raw Data Preview ---
with st.expander("🗂️ Show Raw Data"):
    st.dataframe(df_sesh)
