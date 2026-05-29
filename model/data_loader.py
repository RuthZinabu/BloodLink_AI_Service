import os
from typing import Optional, Tuple

import pandas as pd

BLOOD_TYPES = ["O+", "A+", "B+", "AB+", "O-", "A-", "B-", "AB-"]


def _is_time_series(df: pd.DataFrame) -> bool:
    return 'date' in df.columns or 'ds' in df.columns


def _has_blood_type_columns(df: pd.DataFrame) -> bool:
    return all(bt in df.columns for bt in BLOOD_TYPES)


def _normalize_date_column(df: pd.DataFrame) -> pd.DataFrame:
    if 'ds' in df.columns and 'date' not in df.columns:
        df = df.rename(columns={'ds': 'date'})
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    if df['date'].isna().any():
        raise ValueError('Found invalid date values in the dataset.')
    return df


def _fill_missing_dates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values('date')
    full_range = pd.date_range(start=df['date'].min(), end=df['date'].max(), freq='D')
    df = df.set_index('date').reindex(full_range)
    df.index.name = 'date'

    # Only fill missing values where actual data is missing
    for bt in BLOOD_TYPES:
        if bt in df.columns:
            df[bt] = df[bt].interpolate(method='time', limit_direction='both')
            df[bt] = df[bt].fillna(method='ffill').fillna(method='bfill')
            df[bt] = df[bt].round().astype(int)

    return df.reset_index()


def _load_time_series_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    if not _is_time_series(df):
        raise ValueError(f"{path} is not a time-series dataset.")

    df = _normalize_date_column(df)
    if not _has_blood_type_columns(df):
        raise ValueError(
            f"Loaded {path} but missing expected blood type columns: "
            f"{[bt for bt in BLOOD_TYPES if bt not in df.columns]}"
        )

    df = df[['date'] + BLOOD_TYPES].copy()
    return _fill_missing_dates(df)


def load_historical_demand(data_path: str = None) -> pd.DataFrame:
    """Load historical blood demand data from a real CSV file.

    The loader prefers `data/download.csv` if available with a time-series format
    and falls back to `data/blood_demand_data.csv`.
    """
    candidates = []
    if data_path:
        candidates.append(data_path)
    else:
        candidates.extend([
            os.path.join('data', 'download.csv'),
            os.path.join('data', 'blood_demand_data.csv'),
            os.path.join('data', 'download (3).csv'),
        ])

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            try:
                return _load_time_series_csv(candidate)
            except ValueError:
                continue

    raise FileNotFoundError(
        'No valid historical demand CSV found. Place your real blood demand data at '
        'data/download.csv or fallback to data/blood_demand_data.csv.'
    )
