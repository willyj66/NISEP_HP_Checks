import streamlit as st
import pandas as pd
import plotly.express as px
from getNISEPdata import getTimeseries, getLookup
sites = st.session_state.sites

# --- Sidebar for Control ---
st.sidebar.title("Controls")
site = st.sidebar.multiselect("Select Site", sites)
variable = None  # None for downloading all
past_days = st.sidebar.number_input("Days Displayed", 1, None, 1)


# Retrieve the data from session state
df_sesh = st.session_state.df
temperature_columns = df_sesh.filter(like='Temperature').columns
columns_to_keep = ['datetime'] + list(temperature_columns)
df = df_sesh[columns_to_keep]
df['datetime'] = pd.to_datetime(df['datetime'])  # Ensure 'datetime' is in proper format
# --- Main Content ---
st.title("📊 NISEP Time Series Data")
fig = px.line(df, x='datetime', y=df.columns, title="Heat pump data over the past "+str(st.session_state.past_days)+" days")
st.plotly_chart(fig, use_container_width=True)
# --- Raw Data Preview ---
with st.expander("🗂️ Show Raw Data"):
    st.dataframe(df)  # Show last 10 rows of the data
