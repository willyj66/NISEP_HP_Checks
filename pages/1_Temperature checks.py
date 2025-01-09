import streamlit as st
import pandas as pd
import plotly.express as px
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
