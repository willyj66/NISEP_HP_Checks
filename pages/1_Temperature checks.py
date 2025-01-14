import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from getNISEPdata import getTimeseries

# --- Sidebar for Control ---
st.sidebar.title("Controls")

past_days_new = st.sidebar.number_input("Days Displayed", 1, None, st.session_state.past_days)

# Default boundary settings
default_boundaries = {
    "Flow/Return": {"min": 20, "max": 70},
    "Outdoor": {"min": -30, "max": 50},
    "Indoor": {"min": 18, "max": 26},
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

# --- Main Content ---
st.title("📊 NISEP Time Series Data")

for variable in variable_options:
    # Filter columns corresponding to the current variable
    relevant_columns = [col for col in temperature_columns if col.startswith(variable)]
    if not relevant_columns:
        continue

    # Prepare the data
    df = df_sesh[["datetime"] + relevant_columns]
    df['datetime'] = pd.to_datetime(df['datetime'])

    # Get conditions for the current variable
    conditions = get_conditions(variable)

    # Determine locations with out-of-range data
    out_of_range_locations = [
        col for col in relevant_columns
        if ((df[col] < conditions["min"]) | (df[col] > conditions["max"])).any()
    ]

    if not out_of_range_locations:
        continue  # Skip if no out-of-range data

    # Radio buttons for filtering locations
    selected_location = st.radio(f"Select Location for {variable}", out_of_range_locations, key=variable)

    # Create the plot
    fig = go.Figure()
    for column in relevant_columns:
        # Identify out-of-range data
        out_of_range_mask = (df[column] < conditions["min"]) | (df[column] > conditions["max"])

        if column == selected_location:
            line_style = [
                "solid" if not is_out else "dash"
                for is_out in out_of_range_mask
            ]
            fig.add_trace(go.Scatter(
                x=df["datetime"],
                y=df[column],
                mode="lines",
                name=column,
                line=dict(width=3, color="blue"),
                customdata=line_style,  # Placeholder to allow additional styling
            ))

    fig.update_layout(
        title=f"{variable} Data ({selected_location})",
        xaxis_title="Datetime",
        yaxis_title="Temperature (°C)",
        legend_title="Legend",
        template="plotly_white",
    )

    st.plotly_chart(fig, use_container_width=True)

# --- Raw Data Preview ---
with st.expander("🗂️ Show Raw Data"):
    st.dataframe(df_sesh)
