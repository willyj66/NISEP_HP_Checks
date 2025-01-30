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

# Sidebar controls
st.sidebar.title("Controls")
past_days = st.sidebar.number_input("Days Displayed", 1, 30, 7)

# Main content in an expander
with st.expander("⚙️ Adjust Bounds", expanded=False):
    # Bounds inputs
    bounds = {
        "Flow/Return": {"min": st.number_input("Flow/Return Min", value=10), "max": st.number_input("Flow/Return Max", value=70)},
        "Outdoor": {"min": st.number_input("Outdoor Min", value=-10), "max": st.number_input("Outdoor Max", value=30)},
        "Indoor": {"min": st.number_input("Indoor Min", value=15), "max": st.number_input("Indoor Max", value=26)},
        "Delta T": {"min": st.number_input("Delta T Min", value=-10), "max": st.number_input("Delta T Max", value=10)},
    }

    # Cache Processed Data
    @st.cache_data
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
                        name=f"{site} - {col} (within bounds)",
                        line=dict(color='blue'),
                        showlegend=True  # Show legend for within bounds
                    ))

            # Plot out of bounds data (scatter with joined dots)
            if "out_of_bounds" in site_data and site_data["out_of_bounds"].shape[0] > 0:
                for col in site_data["out_of_bounds"].columns:
                    fig.add_trace(go.Scatter(
                        x=site_data["out_of_bounds"].index,
                        y=site_data["out_of_bounds"][col],
                        mode="markers",  # Scatter with dots joined by lines
                        name=f"{site} - {col} (out of bounds)",
                        marker=dict(color='red', size=4),  # Red dots
                        showlegend=True  # Show legend for out of bounds
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
                )
            )

            # Render the plot in the respective column
            st.plotly_chart(fig, use_container_width=True)
