"""Data transformation utilities for chart rendering.

This module handles conversion of PowerBI tool results (JSON) to pandas DataFrames
with proper type inference and validation.
"""

from typing import List, Dict, Tuple
import pandas as pd


def rows_to_dataframe(rows: List[Dict]) -> pd.DataFrame:
    """
    Convert list of row dictionaries to pandas DataFrame with type inference.

    Features:
    - Automatic datetime parsing for date/time columns
    - Numeric conversion for value columns
    - Handles missing values gracefully

    Args:
        rows: List of dictionaries, each representing a data row

    Returns:
        pandas DataFrame with inferred types
    """
    df = pd.DataFrame(rows)

    # Infer and convert data types
    for col in df.columns:
        col_lower = col.lower()

        # Try datetime conversion for date/time columns
        if any(word in col_lower for word in ['date', 'time', 'year', 'month']):
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except Exception:
                pass  # Keep original type if conversion fails

        # Try numeric conversion for object-type columns
        elif df[col].dtype == 'object':
            try:
                converted = pd.to_numeric(df[col], errors='coerce')
                # Only apply conversion if at least one value converted successfully
                if converted.notna().any():
                    df[col] = converted
            except Exception:
                pass  # Keep as categorical if not numeric

    return df


def validate_dataframe(df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Validate DataFrame for chart rendering.

    Checks:
    - Not empty
    - Has numeric columns
    - Row count within limits

    Args:
        df: pandas DataFrame to validate

    Returns:
        Tuple of (is_valid: bool, error_message: str)
        error_message is empty string if valid
    """
    if df.empty:
        return False, "DataFrame is empty"

    if len(df) == 0:
        return False, "No rows in DataFrame"

    if len(df) > 1000:
        return False, "Too many rows (limit: 1000)"

    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) == 0:
        return False, "No numeric columns found"

    return True, ""
