"""Utility functions for UI and caching."""

import pandas as pd
import hashlib
from typing import Optional, List, Dict


def compute_dataframe_hash(df: pd.DataFrame) -> str:
    """Generate deterministic hash of DataFrame for caching.

    Uses MD5 hashing on pandas object hash for fast cache key generation.
    Includes index=True to ensure changes in row order invalidate cache.

    Args:
        df: DataFrame to hash

    Returns:
        Hexadecimal MD5 hash string for use as cache key
    """
    # Hash based on all values and index for cache correctness.
    hashed = pd.util.hash_pandas_object(df, index=True)
    return hashlib.md5(hashed.values.tobytes()).hexdigest()


def format_dataframe_for_display(
    df: pd.DataFrame,
    float_cols: List[str],
    rename_map: Optional[Dict[str, str]] = None
) -> pd.DataFrame:
    """Format DataFrame for clean UI display.

    Args:
        df: DataFrame to format
        float_cols: List of column names to format as 3-decimal floats
        rename_map: Optional mapping of old column names to new display names

    Returns:
        Formatted DataFrame with float formatting and renamed columns
    """
    df_display = df.copy()

    # Format floats to 3 decimal places
    for col in float_cols:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(lambda x: f"{x:.3f}")

    # Rename columns for display
    if rename_map:
        df_display = df_display.rename(columns=rename_map)

    return df_display
