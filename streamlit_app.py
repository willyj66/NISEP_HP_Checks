import streamlit as st
from getNISEPdata import getTimeseries, getLookup
from datetime import datetime, timedelta

auth_url = st.secrets.get("Login", {}).get("URL", "https://users.carnego.net")
username = st.secrets.get("Login", {}).get("Username", "")
password = st.secrets.get("Login", {}).get("Password", "")
@st.cache_data
def cache_lookup():
    return getLookup(auth_url, username, password)
lookup_df = cache_lookup()
variables = lookup_df.name.unique()
sites = lookup_df.siteNamespace.unique()



variable = st.multiselect("Variable",variables,default=None)
variable = None if not variable else variable
site = st.multiselect("Site",sites,sites[0])
past_days = st.number_input("Days displayed",1,None,1)
end_time = datetime(*datetime.now().timetuple()[:3]) # Get today's date from start of day (i.e. midnight)
start_time = end_time - timedelta(days = past_days) # Look at last day's worth of data
df = getTimeseries(end_time,start_time,site,variable,auth_url, username, password)

st.dataframe(df)