import pandas as pd
import numpy as np
import math

def _sanitize(obj):
    """Recursively convert NaN/Inf values to None for JSON compliance."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, np.generic):
        # Handle numpy types
        if np.isnan(obj):
            return None
        return obj.item() if hasattr(obj, 'item') else obj
    return obj

def serialize_features(features):
    if isinstance(features, pd.DataFrame):
        # replace handles NaN in DataFrames
        return features.replace({np.nan: None, np.inf: None, -np.inf: None}).to_dict(orient="records")
    elif isinstance(features, pd.Series):
        return [features.replace({np.nan: None, np.inf: None, -np.inf: None}).to_dict()]
    elif isinstance(features, (np.ndarray, list, dict)):
        # For other types, use recursive sanitization
        # First convert to standard python types if needed
        if isinstance(features, np.ndarray):
            return _sanitize(features.tolist())
        return _sanitize(features if isinstance(features, list) else [features])
    else:
        raise ValueError("Unsupported features format")
