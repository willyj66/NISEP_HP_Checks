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

# Layout for Expander and Data Display
col1, col2 = st.columns([1, 3])

with col1:
    with st.expander("⚙️ Adjust Bounds", expanded=True):
        bounds = {
            "Flow/Return": {"min": st.number_input("Flow/Return Min", value=10), "max": st.number_input("Flow/Return Max", value=70)},
            "Outdoor": {"min": st.number_input("Outdoor Min", value=-10), "max": st.number_input("Outdoor Max", value=30)},
            "Indoor": {"min": st.number_input("Indoor Min", value=15), "max": st.number_input("Indoor Max", value=26)},
            "Delta T": {"min": st.number_input("Delta T Min", value=-10), "max": st.number_input("Delta T Max", value=10)},
        }

# Cache Processed Data
@st.cache_data
def cache_filtered_data(df, past_days, bounds):
    return process_temperature_and_delta_t_data(df, past_days, bounds)

filtered_data = cache_filtered_data(st.session_state.nisep_df, past_days, bounds)

st.title("📊 Time Series Data")

# Generate all plots at once
figs = []
for site, site_df in filtered_data.items():
    fig = go.Figure()
    for col in site_df.columns:
        fig.add_trace(go.Scatter(x=site_df.index, y=site_df[col], mode="lines", name=f"{site} - {col}"))
    fig.update_layout(title=f"Site: {site}", xaxis_title="Datetime", yaxis_title="Value", template="plotly_white")
    figs.append(fig)

with col2:
    for fig in figs:
        st.plotly_chart(fig, use_container_width=True)
