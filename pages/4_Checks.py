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
    lookup_df = getLookup(auth_url, username, password)
    # Check the past 30 days
    end_time = datetime(*datetime.now().timetuple()[:3]) 
    start_time = end_time - timedelta(days=30)

    return lookup_df.siteNamespace.unique(), getTimeseries(end_time, start_time, None, None, auth_url, username, password)

all_sites, st.session_state.nisep_df = cache_lookup()

st.text(st.session_state.nisep_df.columns)