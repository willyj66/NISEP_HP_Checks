import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from getNISEPdata import getTimeseries

# --- Sidebar for Control ---
st.sidebar.title("Controls")

past_days_new = st.sidebar.number_input("Days Displayed", 1, None, st.session_state.past_days)

if past_days_new != st.session_state.past_days:
    # --- Auth & Data Fetching ---
    auth_url = st.secrets.get("Login", {}).get("URL", "https://users.carnego.net")
    username = st.secrets.get("Login", {}).get("Username", "")
    password = st.secrets.get("Login", {}).get("Password", "")
    end_time = datetime(*datetime.now().timetuple()[:3])  # Today's date from the start of the day
    start_time = end_time - timedelta(days=past_days_new)  # Start time as per selected days
    st.session_state.df = getTimeseries(end_time, start_time, None, None, auth_url, username, password)
    st.session_state.past_days = past_days_new

# Retrieve the data from session state
df_sesh = st.session_state.df
temperature_columns = df_sesh.filter(like='Temperature').columns

# Dynamically update the available variables based on the filtered columns
variable_options = list(set([
    col.split(" (")[0].strip() for col in temperature_columns
]))

# Define conditions
def get_conditions(variable):
    if "Flow" in variable or "Return" in variable:
        return {"min": 20, "max": 70}  # Example Flow/Return conditions
    elif "Outdoor" in variable:
        return {"min": -30, "max": 50}  # Example Outdoor conditions
    else:
        return {"min": 18, "max": 26}  # Example Indoor conditions

# --- Main Content ---
st.title("📊 NISEP Time Series Data")

for variable in variable_options:
    # Filter columns corresponding to the current variable
    relevant_columns = [col for col in temperature_columns if col.startswith(variable)]
    if not relevant_columns:
        continue

    # Prepare the data
    df = df_sesh[["datetime"] + relevant_columns]
    df['datetime'] = pd.to_datetime(df['datetime'])

    # Get conditions for the current variable
    conditions = get_conditions(variable)

    # Create the plot
    fig = go.Figure()
    for column in relevant_columns:
        # Highlight out-of-range data
        df["out_of_range"] = (df[column] < conditions["min"]) | (df[column] > conditions["max"])

        fig.add_trace(go.Scatter(
            x=df["datetime"],
            y=df[column],
            mode="lines",
            name=f"{column} - In Range",
            line=dict(width=2, color="blue"),
            legendgroup=column,
            showlegend=False if len(relevant_columns) > 1 else True,
            opacity=0.6
        ))
        fig.add_trace(go.Scatter(
            x=df["datetime"][df["out_of_range"]],
            y=df[column][df["out_of_range"]],
            mode="lines",
            name=f"{column} - Out of Range",
            line=dict(width=4, color="red"),
            legendgroup=column,
            showlegend=True
        ))

    fig.update_layout(
        title=f"{variable} Data",
        xaxis_title="Datetime",
        yaxis_title="Temperature (°C)",
        legend_title="Legend",
        template="plotly_white",
    )

    st.plotly_chart(fig, use_container_width=True)

# --- Raw Data Preview ---
with st.expander("🗂️ Show Raw Data"):
    st.dataframe(df_sesh)
