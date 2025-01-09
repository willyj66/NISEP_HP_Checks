import streamlit as st
import pandas as pd
import plotly_express as px
# Retrieve the data from session state
df_sesh = st.session_state.df
temperature_columns = df_sesh.filter(like='Temperature').columns
columns_to_keep = ['datetime'] + list(temperature_columns)
df = df_sesh[columns_to_keep]

# Sidebar selection for variables to display
display_variable = st.sidebar.multiselect("Select Variable", df.columns[1:])  # Exclude 'datetime' and last column if it's not relevant

# --- Data Processing ---
if df.empty:
    st.warning("No data available for the selected parameters.")
else:
    df['datetime'] = pd.to_datetime(df['datetime'])  # Ensure 'datetime' is in proper format

    # --- Main Content ---
    st.title("📊 NISEP Time Series Data")

    # Plotting multiple variables using Plotly
    if display_variable:
        fig = px.line(df, x='datetime', y=display_variable, title="Heat pump data over the past "+str(st.session_state.past_days)+" days")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Please select at least one variable to plot.")

    # --- Quick Metrics Section ---
    if display_variable:
        st.subheader("🔍 Quick Metrics")
        for var in display_variable:
            mean_value = df[var].mean() if not df.empty else "N/A"
            st.metric(label=f"Average {var}", value=mean_value)

    # --- Raw Data Preview ---
    with st.expander("🗂️ Show Raw Data"):
        st.dataframe(df)  # Show last 10 rows of the data
