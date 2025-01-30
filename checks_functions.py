import pandas as pd
from datetime import datetime, timedelta
import pytz

def process_temperature_and_delta_t_data(df, past_days, bounds):
    """
    Processes temperature and Delta T time series data for visualization.
    
    Args:
        df (pd.DataFrame): DataFrame with datetime as index and sites/sensors as columns.
        past_days (int): Number of past days to select.
        bounds (dict): Dictionary with temperature and Delta T bounds (min/max values for filtering).

    Returns:
        dict: Dictionary with site names as keys and filtered DataFrames as values.
    """
    # Ensure datetime index is in UK timezone
    uk_tz = pytz.timezone("Europe/London")
    end_time = datetime.now(uk_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(days=past_days)

    # Convert df datetime index to timezone-aware format
    df = df.copy()
    df.index = pd.to_datetime(df.index)  # Ensure index is datetime
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")  # Assume UTC if no timezone
    df.index = df.index.tz_convert("Europe/London")  # Convert to UK time

    # Filter based on UK time range
    df_filtered = df.loc[start_time:end_time]
    
    temperature_columns = df_filtered.filter(like='Temperature').columns
    delta_t_columns = df_filtered.filter(like='Delta T').columns
    all_columns = list(temperature_columns) + list(delta_t_columns)
    
    result = {}

    for column in all_columns:
        variable_type = column.split(" (")[0].strip()
        site_name = column.split(" (")[-1].strip(")") if "(" in column else "Unknown"
        
        # Find appropriate bounds
        if "Flow" in variable_type or "Return" in variable_type:
            min_val, max_val = bounds["Flow/Return"]["min"], bounds["Flow/Return"]["max"]
        elif "Outdoor" in variable_type:
            min_val, max_val = bounds["Outdoor"]["min"], bounds["Outdoor"]["max"]
        elif "Delta T" in variable_type:
            min_val, max_val = bounds["Delta T"]["min"], bounds["Delta T"]["max"]
        else:
            min_val, max_val = bounds["Indoor"]["min"], bounds["Indoor"]["max"]

        # Filter out-of-range values
        mask = (df_filtered[column] < min_val) | (df_filtered[column] > max_val)
        if mask.any():
            result.setdefault(site_name, pd.DataFrame())
            result[site_name][column] = df_filtered[column]

    return result
