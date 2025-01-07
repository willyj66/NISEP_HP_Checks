import streamlit as st
from getNISEPdata import getTimeseries, getLookup
from datetime import datetime, timedelta



site = ['NISEP01']#,'NISEP02']
variable = None#['delta_t', 'flow_rate','flow_temp']
end_time = datetime(*datetime.now().timetuple()[:3]) # Get today's date from start of day (i.e. midnight)
start_time = end_time - timedelta(days = 1) # Look at last day's worth of data
auth_url = st.secrets.get("Login", {}).get("URL", "https://users.carnego.net")
username = st.secrets.get("Login", {}).get("Username", "")
password = st.secrets.get("Login", {}).get("Password", "")
lookup_df = getLookup(auth_url, username, password)
st.dataframe(lookup_df)
df = getTimeseries(end_time,start_time,site,variable,auth_url, username, password)

st.dataframe(df)