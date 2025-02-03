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
st.logo('logo.svg', size='large')

# --- Authentication & Data Fetching ---
auth_url = st.secrets.get("Login", {}).get("URL", "https://users.carnego.net")
username = st.secrets.get("Login", {}).get("Username", "")
password = st.secrets.get("Login", {}).get("Password", "")

@st.cache_resource(ttl="1d")
def cache_nisep():
    """Fetch lookup data and timeseries data, caching the results for one day."""
    lookup_df = getLookup(auth_url, username, password)
    end_time = datetime(*datetime.now().timetuple()[:3])
    start_time = end_time - timedelta(days=30)
    timeseries_df = getTimeseries(end_time, start_time, None, None, auth_url, username, password)
    return lookup_df.siteNamespace.unique(), timeseries_df

all_sites, st.session_state.nisep_df = cache_nisep()

# --- Temperature Checks ---
with st.expander("⚙️ Temperature Checks", expanded=False):
    past_days = st.number_input("Days Displayed", 1, 30, 2)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.subheader("Flow/Return")
        flow_return_min = st.number_input("Min", value=10)
        flow_return_max = st.number_input("Max", value=70)

    with col2:
        st.subheader("Outdoor")
        outdoor_min = st.number_input("Min", value=-10)
        outdoor_max = st.number_input("Max", value=30)

    with col3:
        st.subheader("Indoor")
        indoor_min = st.number_input("Min", value=15)
        indoor_max = st.number_input("Max", value=26)

    with col4:
        st.subheader("Delta T")
        delta_t_min = st.number_input("Min", value=-10)
        delta_t_max = st.number_input("Max", value=10)

    bounds = {
        "Flow/Return": {"min": flow_return_min, "max": flow_return_max},
        "Outdoor": {"min": outdoor_min, "max": outdoor_max},
        "Indoor": {"min": indoor_min, "max": indoor_max},
        "Delta T": {"min": delta_t_min, "max": delta_t_max},
    }

    filtered_data = process_temperature_and_delta_t_data(st.session_state.nisep_df, past_days, bounds, all_sites)

    site_columns = st.columns(2)
    for idx, (site, site_data) in enumerate(filtered_data.items()):
        col = site_columns[idx % 2]
        with col:
            fig = go.Figure()
            for key, color in [("within_bounds", 'blue'), ("out_of_bounds", 'red')]:
                if key in site_data and not site_data[key].empty:
                    for column in site_data[key].columns:
                        fig.add_trace(go.Scatter(
                            x=site_data[key].index, y=site_data[key][column],
                            mode="lines" if key == "within_bounds" else "markers",
                            name=f"{column} ({key.replace('_', ' ')})",
                            line=dict(color=color) if key == "within_bounds" else None,
                            marker=dict(color=color, size=4) if key == "out_of_bounds" else None,
                            showlegend=False
                        ))
            fig.update_layout(
                title=f"Site: {site}",
                xaxis=dict(title="Datetime"),
                yaxis_title="Temperature [°C]",
                template="plotly_white",
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig, use_container_width=True)

# --- Missing Data Analysis ---
def calculate_missing_data_percentage(data):
    """Calculate percentage of missing data for each column."""
    return (data.isna().sum() / len(data)) * 100

uk_tz = pytz.timezone("Europe/London")
end_time = datetime.now(uk_tz)

intervals = {
    "Daily": end_time - timedelta(days=1),
    "Weekly": end_time - timedelta(days=7),
    "Monthly": end_time - timedelta(days=30),
}

missing_data_df = pd.DataFrame({
    interval: st.session_state.nisep_df.loc[start:end_time].replace(0, pd.NA).apply(calculate_missing_data_percentage)
    for interval, start in intervals.items()
}).fillna(0)

site_groups = {}
for row_name in missing_data_df.index:
    match = re.search(r"\((NISEP\d{2})\)", row_name)
    if match:
        site_id = match.group(1)
        site_groups.setdefault(site_id, {})[row_name] = missing_data_df.loc[row_name]

site_groups = {k: pd.DataFrame(v).T.round(1) for k, v in site_groups.items()}

with st.expander("📊 Missing Data Analysis by Site"):
    col1, col2 = st.columns(2)
    for idx, (site_id, df) in enumerate(site_groups.items()):
        df_display = df.applymap(lambda x: f"{x:.1f}")
        with (col1 if idx % 2 == 0 else col2):
            st.subheader(f"📍 Site: {site_id}")
            st.dataframe(df_display.style.applymap(lambda v: 'background-color: red' if float(v) > 30 else ''), height=350)

# --- COP Analysis ---
def get_sliced_data(df, interval):
    """Extract data for given interval and resample appropriately."""
    sliced_df = df.loc[intervals[interval]:end_time]
    return sliced_df.resample('D' if interval in ["Monthly", "Weekly"] else 'H').max()

with st.expander("⚡ COP Analysis", expanded=False):
    cop_data = pd.DataFrame()
    heat_diff_data = pd.DataFrame()
    consumption_diff_data = pd.DataFrame()

    for interval in intervals.keys():
        interval_df = get_sliced_data(st.session_state.nisep_df, interval)
        interval_cop, interval_heat_diff, interval_consumption_diff = calculate_cop(interval_df)
        for df, name in [(interval_cop, "COP"), (interval_heat_diff, "Heat Diff"), (interval_consumption_diff, "Consumption Diff")]:
            df.rename(columns={df.columns[0]: interval}, inplace=True)
            cop_data, heat_diff_data, consumption_diff_data = [df if df.empty else df.merge(df, left_index=True, right_index=True, how="outer") for df in [cop_data, heat_diff_data, consumption_diff_data]]

    st.subheader("📊 Heat Pump COP Analysis")
    for col, title, df in zip(st.columns(3), ["Heat Diff", "Consumption Diff", "COP"], [heat_diff_data, consumption_diff_data, cop_data]):
        with col:
            st.subheader(title)
            st.dataframe(df.style.applymap(lambda x: 'background-color: red' if float(x) < 1 or float(x) > 6 else ''), use_container_width=True)
