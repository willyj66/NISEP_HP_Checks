import streamlit as st
from getNISEPdata import getTimeseries, getLookup
from datetime import datetime, timedelta
import plotly.graph_objects as go
import pandas as pd

# Page layout configuration
st.set_page_config(layout="wide")

# --- Auth & Data Fetching ---
auth_url = st.secrets.get("Login", {}).get("URL", "https://users.carnego.net")
username = st.secrets.get("Login", {}).get("Username", "")
password = st.secrets.get("Login", {}).get("Password", "")

# Cache Lookup Data
@st.cache_data
def cache_lookup():
    return getLookup(auth_url, username, password)

lookup_df = cache_lookup()
all_sites = lookup_df.siteNamespace.unique()


# --- Helper Functions ---
def update_data(past_days, current_display_site, current_variable_1, current_variable_2):
    end_time = datetime(*datetime.now().timetuple()[:3])  # Today's date from the start of the day
    start_time = end_time - timedelta(days=past_days)

    df = getTimeseries(end_time, start_time, None, None, auth_url, username, password)

    # Filter available columns based on the selected sites
    if current_display_site:
        site_columns = [
            col for col in df.columns if any(f"({site})" in col for site in current_display_site)
        ]
    else:
        site_columns = df.columns[1:]  # Exclude 'datetime'

    # Dynamically update the available variables based on the filtered columns
    variable_options = list(set([col.split(" (")[0].strip() for col in site_columns]))

    # Filter the dataframe to include only relevant columns
    filtered_columns = ["datetime"] + [
        col for col in site_columns if col.split(" (")[0].strip() in current_variable_1 + current_variable_2
    ]

    # Update session state only after data update is complete
    st.session_state.df = df
    st.session_state.site_columns = site_columns
    st.session_state.variable_options = variable_options
    st.session_state.filtered_columns = filtered_columns
    st.session_state.current_display_site = current_display_site
    st.session_state.current_variable_1 = current_variable_1
    st.session_state.current_variable_2 = current_variable_2

    return df, site_columns, variable_options, filtered_columns


# --- Sidebar for Control ---
st.sidebar.title("Controls")

# Days Displayed Input
past_days = st.sidebar.number_input("Days Displayed", 1, None, 1)

# Retrieve data from session state or update with new selections
if 'past_days' not in st.session_state or st.session_state.past_days != past_days:
    df, site_columns, variable_options, filtered_columns = update_data(past_days, [], [], [])
else:
    df = st.session_state.df
    site_columns = st.session_state.site_columns
    variable_options = st.session_state.variable_options
    filtered_columns = st.session_state.filtered_columns

# Update session state with selections if they have changed
if (
    'current_display_site' not in st.session_state
    or st.session_state.current_display_site != current_display_site
    or 'current_variable_1' not in st.session_state
    or st.session_state.current_variable_1 != current_variable_1
    or 'current_variable_2' not in st.session_state
    or st.session_state.current_variable_2 != current_variable_2
):
    df, site_columns, variable_options, filtered_columns = update_data(
        past_days, current_display_site, current_variable_1, current_variable_2
    )

# Sidebar Site Selection
current_display_site = st.sidebar.multiselect(
    "Select Site",
    all_sites,
    key="display_site",
)

# Sidebar Variable Selection
current_variable_1 = st.sidebar.multiselect(
    "Select Variable 1 (Y1)",
    variable_options,
    key="variable_1",
)

current_variable_2 = st.sidebar.multiselect(
    "Select Variable 2 (Y2)",
    variable_options,
    key="variable_2",
)

# --- Data Processing ---
if df.empty:
    st.warning("No data available for the selected parameters.")
else:
    # Ensure 'datetime' is in proper format
    df['datetime'] = pd.to_datetime(df['datetime'])

    # --- Main Content ---
    st.title("📊 NISEP Time Series Data")

    if current_variable_1 or current_variable_2:
        # Create the Plotly figure
        fig = go.Figure()

        # Add traces for Variable 1 (Y1)
        for var in current_variable_1:
            cols = [col for col in site_columns if col.startswith(var)]
            for col in cols:
                fig.add_trace(go.Scatter(x=df['datetime'], y=df[col], mode='lines', name=f"{col} (Y1)", yaxis="y1"))

        # Add traces for Variable 2 (Y2)
        for var in current_variable_2:
            cols = [col for col in site_columns if col.startswith(var)]
            for col in cols:
                fig.add_trace(go.Scatter(x=df['datetime'], y=df[col], mode='lines', name=f"{col} (Y2)", yaxis="y2"))

        # Configure axes with dynamic labels and place legend to the right of the plot
        fig.update_layout(
            title=f"Heat pump data over the past {st.session_state.past_days} days",
            xaxis=dict(title="Datetime"),
            yaxis=dict(title=", ".join(current_variable_1) if current_variable_1 else "Y1 Variables"),
            yaxis2=dict(
                title=", ".join(current_variable_2) if current_variable_2 else "Y2 Variables",
                overlaying="y",
                side="right"
            ),
            legend=dict(
                orientation="v",  # Vertical orientation
                x=1.05,          # Place it slightly to the right of the plot
                y=1,             # Align it to the top
                xanchor="left",  # Anchor it from the left
                yanchor="top"   # Anchor it from the top
            )
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Please select at least one variable to plot.")

    # --- Raw Data Preview ---
    with st.expander("🗂️ Show Raw Data"):
        st.dataframe(df[filtered_columns])  # Show filtered data for the selected columns