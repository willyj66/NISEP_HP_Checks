import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from getNISEPdata import getTimeseries

# Page layout configuration
st.set_page_config(layout="wide")

# --- Sidebar for Control ---
st.sidebar.title("Controls")
if 'past_days' not in st.session_state:
    st.session_state.past_days = 1
past_days_new = st.sidebar.number_input("Days Displayed", 1, None, st.session_state.past_days)

# Updated default boundary settings
default_boundaries = {
    "Flow/Return": {"min": 10, "max": 70},
    "Outdoor": {"min": -10, "max": 30},
    "Indoor": {"min": 15, "max": 26},
    "Delta T": {"min": -10, "max": 10},  # Added Delta T boundary
}

# Sidebar expander for range adjustments
with st.sidebar.expander("Adjust Boundaries"):
    flow_min = st.number_input("Flow/Return Min", value=default_boundaries["Flow/Return"]["min"])
    flow_max = st.number_input("Flow/Return Max", value=default_boundaries["Flow/Return"]["max"])
    outdoor_min = st.number_input("Outdoor Min", value=default_boundaries["Outdoor"]["min"])
    outdoor_max = st.number_input("Outdoor Max", value=default_boundaries["Outdoor"]["max"])
    indoor_min = st.number_input("Indoor Min", value=default_boundaries["Indoor"]["min"])
    indoor_max = st.number_input("Indoor Max", value=default_boundaries["Indoor"]["max"])
    delta_t_min = st.number_input("Delta T Min", value=default_boundaries["Delta T"]["min"])  # Delta T Min
    delta_t_max = st.number_input("Delta T Max", value=default_boundaries["Delta T"]["max"])  # Delta T Max

if past_days_new != st.session_state.past_days or 'df' not in st.session_state:
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

# Dynamically filter temperature and delta T columns
temperature_columns = df_sesh.filter(like='Temperature').columns
delta_t_columns = df_sesh.filter(like='Delta T').columns  # Filter Delta T columns

# Combine temperature and delta T columns
all_columns = list(temperature_columns) + list(delta_t_columns)

# Dynamically update the available variables based on the filtered columns
variable_options = list(set([
    col.split(" (")[0].strip() for col in all_columns
]))

# Function to determine min/max values based on variable type
def get_conditions(variable):
    if "Flow" in variable or "Return" in variable:
        return {"min": flow_min, "max": flow_max}
    elif "Outdoor" in variable:
        return {"min": outdoor_min, "max": outdoor_max}
    elif "Delta T" in variable:  # Added condition for Delta T
        return {"min": delta_t_min, "max": delta_t_max}
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
    # Filter columns corresponding to the current variable (includes both temperature and delta T)
    relevant_columns = [col for col in all_columns if col.startswith(variable)]
    if not relevant_columns:
        continue

    # Check if the relevant columns exist in the DataFrame
    missing_columns = [col for col in relevant_columns if col not in df_sesh.columns]
    if missing_columns:
        st.warning(f"Missing columns for {variable}: {', '.join(missing_columns)}")
        continue

    # Prepare the data
    df = df_sesh[["datetime"] + relevant_columns]
    df['datetime'] = pd.to_datetime(df['datetime'])

    # Get conditions for the current variable
    conditions = get_conditions(variable)

    # Extract location IDs
    locations = {col: extract_location(col) for col in relevant_columns}

    # Determine locations with out-of-range data, including Delta T
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

        # Add in-range data (hidd
