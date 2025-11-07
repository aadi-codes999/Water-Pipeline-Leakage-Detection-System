# utils/predict.py
import joblib
import numpy as np
from pathlib import Path

MODEL_PATH = Path("model/leak_detection_model.pkl")

def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}")
    return joblib.load(MODEL_PATH)

def predict_sample(model, supplied, consumed, flow_rate, pressure):
    arr = np.array([[supplied, consumed, flow_rate, pressure]])
    pred = model.predict(arr)
    # model.predict returns 0/1
    return int(pred[0])

def predict_with_flexible_columns(model, df):
    """
    Predict leaks from a dataframe with flexible column name handling.
    Returns both predictions and processed dataframe.
    """
    # Map of possible column names to standard names
    column_variants = {
        'water_supplied_litres': [
            'water_supplied_litres', 'water_supplied_liters', 'water_supplied', 
            'supplied_litres', 'supplied_liters', 'supplied', 'watersupplied'
        ],
        'water_consumed_litres': [
            'water_consumed_litres', 'water_consumed_liters', 'water_consumed', 
            'consumed_litres', 'consumed_liters', 'consumed', 'waterconsumed'
        ],
        'flowrate_lps': [
            'flowrate_lps', 'flow_rate_lps', 'flow_rate', 'flowrate', 'flow',
            'flow_lps', 'water_flow', 'water_flow_rate'
        ],
        'pressure_psi': [
            'pressure_psi', 'pressure', 'psi', 'water_pressure', 
            'pipe_pressure', 'pressure_reading'
        ]
    }

    # Make column names case-insensitive
    df.columns = df.columns.str.lower().str.strip()
    
    # Find the actual column names in the dataframe
    column_mapping = {}
    for standard, variants in column_variants.items():
        found = False
        variants = [v.lower() for v in variants]  # Make variants case-insensitive
        for variant in variants:
            if variant in df.columns:
                column_mapping[standard] = variant
                found = True
                break
        if not found:
            raise ValueError(
                f"Could not find any variant of {standard} in the CSV.\n"
                f"Required measurement: {standard}\n"
                f"Acceptable column names: {', '.join(variants)}\n"
                f"Available columns in file: {', '.join(df.columns)}"
            )
    
    # Create a copy of the dataframe with mapped columns
    feature_cols = ['water_supplied_litres', 'water_consumed_litres', 'flowrate_lps', 'pressure_psi']
    X = df[[column_mapping[col] for col in feature_cols]].copy()
    
    # Rename columns to match training data format
    X.columns = feature_cols
    
    # Basic validation of values
    for col in feature_cols:
        if not np.issubdtype(X[col].dtype, np.number):
            raise ValueError(f"Column {col} contains non-numeric values")
        if X[col].isnull().any():
            raise ValueError(f"Column {col} contains missing values")
        if (X[col] < 0).any():
            raise ValueError(f"Column {col} contains negative values")
    
    return model.predict(X.values), X  # Return both predictions and processed dataframe

def predict_dataframe(model, df):
    """Legacy function that calls predict_with_flexible_columns for backwards compatibility."""
    predictions, _ = predict_with_flexible_columns(model, df)
    return predictions
