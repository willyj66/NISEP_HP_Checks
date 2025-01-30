import pandas as pd
from datetime import datetime, timedelta
import pytz

def process_temperature_and_delta_t_data(df, past_days, bounds, subsample_freq='20T'):
    """
    Processes temperature and Delta T time series data for visualization.
    
    Args:
        df (pd.DataFrame): DataFrame with datetime as index and sites/sensors as columns.
        past_days (int): Number of past days to select.
        bounds (dict): Dictionary with temperature and Delta T bounds (min/max values for filtering).
        subsample_freq (str): Frequency for resampling the in-bounds data (default is every 20 minutes).
    
    Returns:
        dict: Dictionary with site names as keys and two DataFrames as values:
            - 'out_of_bounds': DataFrame containing out-of-bounds values for plotting in red.
            - 'within_bounds': DataFrame with out-of-bounds values replaced by None, subsampled every 20 minutes.
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
            # Create DataFrame for out-of-bounds data
            out_of_bounds_df = df_filtered[mask][[column]]
            result.setdefault(site_name, {"out_of_bounds": pd.DataFrame(), "within_bounds": pd.DataFrame()})
            result[site_name]["out_of_bounds"] = out_of_bounds_df

            # Replace out-of-bounds data with None in the original DataFrame
            within_bounds_df = df_filtered.copy()
            within_bounds_df[column] = within_bounds_df[column].where(~mask)

            # Subsample in-bounds data every 20 minutes
            within_bounds_df_resampled = within_bounds_df[column].resample(subsample_freq).first()
            result[site_name]["within_bounds"] = within_bounds_df_resampled.to_frame()

    return result
