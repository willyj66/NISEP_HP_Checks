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
import pandas as pd
from datetime import datetime, timedelta

def process_temperature_and_delta_t_data(df, past_days, bounds):
    """
    Processes temperature and Delta T time series data for visualization.
    
    Args:
        df (pd.DataFrame): DataFrame with a datetime column and sites/sensors as columns.
        past_days (int): Number of past days to select.
        bounds (dict): Dictionary with temperature and Delta T bounds (min/max values for filtering).

    Returns:
        dict: Dictionary with site names as keys and filtered DataFrames as values.
    """
    df = df.copy()  # Avoid modifying original dataframe
    df["datetime"] = pd.to_datetime(df["datetime"])  # Ensure datetime column is in datetime format
    df.set_index("datetime", inplace=True)  # Set datetime as index

    end_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(days=past_days)

    df_filtered = df.loc[start_time:end_time]  # Now this should work correctly
    
    temperature_columns = df_filtered.filter(like='Temperature').columns
    delta_t_columns = df_filtered.filter(like='Delta T').columns
    all_columns = list(temperature_columns) + list(delta_t_columns)
    
    result = {}

    for column in all_columns:
        variable_type = column.split(" (")[0].strip()
        site_name = column.split(" (")[-1].strip(")") if "(" in column else "Unknown"
        
        # Find appropriate bounds
        if "Flow" in variable_type or "Return" in variable_type:
            min_val, max_val = bounds["Flow/Return"]["min"], bounds["Flow/Return"]["max"]
        elif "Outdoor" in variable_type:
            min_val, max_val = bounds["Outdoor"]["min"], bounds["Outdoor"]["max"]
        elif "Delta T" in variable_type:
            min_val, max_val = bounds["Delta T"]["min"], bounds["Delta T"]["max"]
        else:
            min_val, max_val = bounds["Indoor"]["min"], bounds["Indoor"]["max"]

        # Filter out-of-range values
        mask = (df_filtered[column] < min_val) | (df_filtered[column] > max_val)
        if mask.any():
            result.setdefault(site_name, pd.DataFrame())
            result[site_name][column] = df_filtered[column]

    return result
