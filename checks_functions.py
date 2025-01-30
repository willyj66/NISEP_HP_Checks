import pandas as pd
from datetime import datetime, timedelta

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
    end_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(days=past_days)
    
    df_filtered = df.loc[start_time:end_time]
    temperature_columns = df_filtered.filter(like='Temperature').columns
    delta_t_columns = df_filtered.filter(like='Delta T').columns
    all_columns = list(temperature_columns) + list(delta_t_columns)
    
    result = {}
    
    for column in all_columns:
        variable_type = column.split(" (")[0].strip()
        site_name = column.split(" (")[-1].strip(")") if "(" in column else "Unknown"
        
        if variable_type in bounds:
            min_val, max_val = bounds[variable_type]['min'], bounds[variable_type]['max']
            mask = (df_filtered[column] < min_val) | (df_filtered[column] > max_val)
            if mask.any():
                result.setdefault(site_name, pd.DataFrame())
                result[site_name][column] = df_filtered[column]
    
    return result
