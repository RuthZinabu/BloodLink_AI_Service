import os
import pandas as pd

BLOOD_TYPES = ["O+", "A+", "B+", "AB+", "O-", "A-", "B-", "AB-"]


def load_historical_demand(data_path: str = None) -> pd.DataFrame:
    """Load historical blood demand data from a real CSV file.

    The loader prefers `data/download.csv` if available and falls back to
    `data/blood_demand_data.csv`.
    """
    candidates = []
    if data_path:
        candidates.append(data_path)
    else:
        candidates.extend([
            os.path.join("data", "download.csv"),
            os.path.join("data", "blood_demand_data.csv"),
            os.path.join("data", "download (3).csv"),
        ])

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            df = pd.read_csv(candidate)
            if 'date' not in df.columns and 'ds' in df.columns:
                df = df.rename(columns={'ds': 'date'})

            if 'date' not in df.columns:
                raise ValueError(
                    f"Loaded {candidate} but it does not contain a 'date' column. "
                    "Your file must include a date column plus one column for each blood type: "
                    f"{BLOOD_TYPES}."
                )

            missing = [bt for bt in BLOOD_TYPES if bt not in df.columns]
            if missing:
                raise ValueError(
                    f"Loaded {candidate} but missing expected blood type columns: {missing}. "
                    "Please provide a real historical demand dataset with columns for all blood types."
                )

            df = df.copy()
            df['date'] = pd.to_datetime(df['date'])
            return df[['date'] + BLOOD_TYPES]

    raise FileNotFoundError(
        "No historical demand CSV found. Place your real blood demand data at "
        "data/download.csv or provide a custom path using --data-file."
    )
