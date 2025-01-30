import streamlit as st
from getNISEPdata import getTimeseries, getLookup
from checks_functions import process_temperature_and_delta_t_data
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
    lookup_df = getLookup(auth_url, username, password)
    end_time = datetime(*datetime.now().timetuple()[:3]) 
    start_time = end_time - timedelta(days=30)
    return lookup_df.siteNamespace.unique(), getTimeseries(end_time, start_time, None, None, auth_url, username, password)

all_sites, st.session_state.nisep_df = cache_lookup()
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
                yaxis_title="Value",
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
