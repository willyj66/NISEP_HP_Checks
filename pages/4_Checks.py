import streamlit as st
from getNISEPdata import getTimeseries, getLookup
from checks_functions import process_temperature_and_delta_t_data, calculate_cop
from datetime import datetime, timedelta
import plotly.graph_objects as go
import pandas as pd
import re
import pytz

# Page layout configuration
st.set_page_config(
    page_title="NISEP Heat Pumpz",
    page_icon="favicon.png",
    layout="wide"
)
st.logo('logo.svg',size='large')

#################### LOGIN #######################

# --- Auth & Data Fetching ---
auth_url = st.secrets.get("Login", {}).get("URL", "https://users.carnego.net")
username = st.secrets.get("Login", {}).get("Username", "")
password = st.secrets.get("Login", {}).get("Password", "")

# Cache Lookup Data
@st.cache_data
def cache_lookup():
    lookup_df = getLookup(auth_url, username, password)
    end_time = datetime(*datetime.now().timetuple()[:3]) 
    start_time = end_time - timedelta(days=30)
    return lookup_df.siteNamespace.unique(), getTimeseries(end_time, start_time, None, None, auth_url, username, password)

all_sites, st.session_state.nisep_df = cache_lookup()


#################### TEMPERATURE CHECKS #######################

# Main content in an expander
with st.expander("⚙️ Temperature Checks", expanded=False):
    past_days = st.number_input("Days Displayed", 1, 30, 2)
    # Create 4 columns for the bounds inputs
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.subheader("Flow/Return")
        flow_return_min = st.number_input("Min", value=10, key="flow_return_min")
        flow_return_max = st.number_input("Max", value=70, key="flow_return_max")

    with col2:
        st.subheader("Outdoor")
        outdoor_min = st.number_input("Min", value=-10, key="outdoor_min")
        outdoor_max = st.number_input("Max", value=30, key="outdoor_max")

    with col3:
        st.subheader("Indoor")
        indoor_min = st.number_input("Min", value=15, key="indoor_min")
        indoor_max = st.number_input("Max", value=26, key="indoor_max")

    with col4:
        st.subheader("Delta T")
        delta_t_min = st.number_input("Min", value=-10, key="delta_t_min")
        delta_t_max = st.number_input("Max", value=10, key="delta_t_max")

    bounds = {
        "Flow/Return": {"min": flow_return_min, "max": flow_return_max},
        "Outdoor": {"min": outdoor_min, "max": outdoor_max},
        "Indoor": {"min": indoor_min, "max": indoor_max},
        "Delta T": {"min": delta_t_min, "max": delta_t_max},
    }

    # Cache Processed Data
    #@st.cache_data
    def cache_filtered_data(df, past_days, bounds, site_names):
        return process_temperature_and_delta_t_data(df, past_days, bounds, site_names)

    filtered_data = cache_filtered_data(st.session_state.nisep_df, past_days, bounds, all_sites)

    # Define grid size based on number of sites
    num_sites = len(filtered_data)
    columns = 2  # 2 columns for the grid layout
    rows = (num_sites // columns) + (1 if num_sites % columns > 0 else 0)  # Calculate number of rows needed

    # Create columns for displaying plots
    site_columns = st.columns(columns)

    # Generate all plots at once
    for idx, (site, site_data) in enumerate(filtered_data.items()):
        # Get the column for the current site
        col = site_columns[idx % columns]  # Ensure it wraps around to the next column if needed

        with col:
            fig = go.Figure()

            # Plot within bounds data (blue line)
            if "within_bounds" in site_data and site_data["within_bounds"].shape[0] > 0:
                for col in site_data["within_bounds"].columns:
                    fig.add_trace(go.Scatter(
                        x=site_data["within_bounds"].index,
                        y=site_data["within_bounds"][col],
                        mode="lines",
                        name=f"{col} (within bounds)",
                        line=dict(color='blue'),
                        showlegend=False  # Show legend for within bounds
                    ))

            # Plot out of bounds data (scatter with joined dots)
            if "out_of_bounds" in site_data and site_data["out_of_bounds"].shape[0] > 0:
                for col in site_data["out_of_bounds"].columns:
                    fig.add_trace(go.Scatter(
                        x=site_data["out_of_bounds"].index,
                        y=site_data["out_of_bounds"][col],
                        mode="markers",  # Scatter with dots joined by lines
                        name=f"{col} (out of bounds)",
                        marker=dict(color='red', size=4),  # Red dots
                        showlegend=False  # Show legend for out of bounds
                    ))

            # Update layout with titles, axes labels, and legend placement
            fig.update_layout(
                title=f"Site: {site}",
                xaxis=dict(title="Datetime"),
                yaxis_title="Temperature [°C]",
                template="plotly_white",
                legend=dict(
                    orientation="h",  # Horizontal legend
                    yanchor="bottom",  # Position the legend below the plot
                    y=-0.2,  # Move legend below the plot
                    xanchor="center",
                    x=0.5
                ),
                hoverlabel_namelength=-1
            )


            # Render the plot in the respective column
            st.plotly_chart(fig, use_container_width=True)


#################### COMPLETENESS CHECKS #######################


def calculate_missing_data_percentage(data):
    """Calculate percentage of missing data for each column in the dataframe."""
    missing_data_percentage = {}
    for column in data.columns:
        missing_count = data[column].isna().sum()
        total_count = len(data[column])
        missing_data_percentage[column] = (missing_count / total_count) * 100
    return missing_data_percentage

# --- Replace Zeros with NaN (None) ---
# --- Subsample the data for different intervals (Daily, Weekly, Monthly) ---
uk_tz = pytz.timezone("Europe/London")
end_time = datetime.now(uk_tz).replace(hour=0, minute=0, second=0, microsecond=0)

# Store missing data percentages for each interval
data_intervals = {
    "Daily": st.session_state.nisep_df.loc[(end_time - timedelta(days=1)):end_time],
    "Weekly": st.session_state.nisep_df.loc[(end_time - timedelta(days=7)):end_time],
    "Monthly": st.session_state.nisep_df.loc[(end_time - timedelta(days=30)):end_time],
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
    site_groups[site_id] = site_groups[site_id].loc[~(site_groups[site_id] < 1).all(axis=1)].round(1)

# --- Highlight Values > 30 in Red ---
def highlight_high_values(val):
    """Highlight values greater than 30 in red."""
    return 'background-color: red' if float(val) > 30 else ''

# --- Display Data ---
with st.expander("📊 Missing Data Analysis by Site"):
    # Create two-column layout
    col1, col2 = st.columns(2)

    # Loop through the site_groups and display each site in alternating columns
    site_list = list(site_groups.items())
    for idx, (site_id, df) in enumerate(site_list):
        # Ensure same vertical space by setting a fixed height for the DataFrame display
        df = df.round(1)  # Make sure rounding happens before display

        # Format the dataframe to remove unnecessary trailing zeros
        df_display = df.applymap(lambda x: f"{x:.1f}" if pd.notnull(x) else "")  # Format to 1 decimal place

        # Alternate between columns for each site
        if idx % 2 == 0:
            with col1:
                st.subheader(f"📍 Site: {site_id}")
                st.dataframe(df_display.style.applymap(highlight_high_values), height=350)  # Fixed height for uniform display
        else:
            with col2:
                st.subheader(f"📍 Site: {site_id}")
                st.dataframe(df_display.style.applymap(highlight_high_values), height=350)  # Fixed height for uniform display


# --- Function to slice data efficiently ---
def get_sliced_data(df, interval):
    uk_tz = pytz.timezone("Europe/London")
    end_time = datetime.now(uk_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    
    start_times = {
        "Daily": end_time - timedelta(days=1),
        "Weekly": end_time - timedelta(days=7),
        "Monthly": end_time - timedelta(days=30),
    }
    
    return df.loc[start_times[interval]:end_time]

# --- COP Analysis Expander ---
with st.expander("⚡ COP Analysis", expanded=False):
    st.sidebar.title("Controls")
    averaging = st.sidebar.selectbox("Averaging Type", ['max', 'min', 'average'])
    
    # Use the cached data and slice instead of refetching
    data_intervals = {interval: get_sliced_data(st.session_state.nisep_df, interval) for interval in ["Daily", "Weekly", "Monthly"]}
    
    cop_data = pd.DataFrame()
    heat_diff_data = pd.DataFrame()
    consumption_diff_data = pd.DataFrame()
    
    for interval, data in data_intervals.items():
        if "datetime" in data.columns:
            data = data.drop(columns=['datetime'])  # Drop datetime if present
        
        interval_cop, interval_heat_diff, interval_consumption_diff = calculate_cop(data)
        interval_cop = interval_cop.rename(columns={"COP": interval})
        interval_heat_diff = interval_heat_diff.rename(columns={"Heat Diff": interval})
        interval_consumption_diff = interval_consumption_diff.rename(columns={"Consumption Diff": interval})

        if cop_data.empty:
            cop_data = interval_cop
            heat_diff_data = interval_heat_diff
            consumption_diff_data = interval_consumption_diff
        else:
            cop_data = cop_data.merge(interval_cop, left_index=True, right_index=True, how="outer")
            heat_diff_data = heat_diff_data.merge(interval_heat_diff, left_index=True, right_index=True, how="outer")
            consumption_diff_data = consumption_diff_data.merge(interval_consumption_diff, left_index=True, right_index=True, how="outer")
    
    st.title("📊 Heat Pump COP Analysis")
    st.write("Below is the analysis for different time intervals:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Heat Diff")
        st.dataframe(heat_diff_data)
    
    with col2:
        st.subheader("Consumption Diff")
        st.dataframe(consumption_diff_data)
    
    with col3:
        st.subheader("COP")
        st.dataframe(cop_data)
