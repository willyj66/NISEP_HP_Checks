import pandas as pd
from datetime import datetime, timedelta

def process_temperature_and_delta_t_data(df, past_days, bounds):
    """
    Processes temperature and Delta T time series data for visualization.
    
    Args:
        df (pd.DataFrame): DataFrame with a datetime column and sites/sensors as columns.
        past_days (int): Number of past days to select.
        bounds (dict): Dictionary with temperature and Delta T bounds (min/max values for filtering).

    Returns:
        dict: Dictionary with site names as keys and filtered DataFrames as values.
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=past_days)
    print(df)
    df_filtered = df.loc[start_time:end_time]  # Now this should work correctly
    
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
