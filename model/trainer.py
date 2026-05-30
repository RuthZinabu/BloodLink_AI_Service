import os
import json
from datetime import datetime
from typing import Dict

import pandas as pd
import pickle
from prophet import Prophet

from model.data_loader import BLOOD_TYPES, _normalize_date_column


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(ROOT, 'data')
MODEL_DIR = os.path.join(ROOT, 'model_files')
METADATA_PATH = os.path.join(MODEL_DIR, 'metadata.json')
TRAINING_STATUS_PATH = os.path.join(MODEL_DIR, 'training_status.json')


def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)


def _read_metadata() -> Dict:
    if not os.path.exists(METADATA_PATH):
        return {"versions": [], "latest": None}
    with open(METADATA_PATH, 'r') as f:
        return json.load(f)


def _write_metadata(meta: Dict):
    with open(METADATA_PATH, 'w') as f:
        json.dump(meta, f, indent=2, default=str)


def _update_training_status(status: Dict):
    with open(TRAINING_STATUS_PATH, 'w') as f:
        json.dump(status, f, indent=2, default=str)


def validate_uploaded_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Normalize dates
    if 'ds' in df.columns and 'date' not in df.columns:
        df = df.rename(columns={'ds': 'date'})
    if 'date' not in df.columns:
        raise ValueError('Missing required `date` column')
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    if df['date'].isna().any():
        raise ValueError('Found invalid date values in the dataset.')

    # Check for blood type columns
    missing = [bt for bt in BLOOD_TYPES if bt not in df.columns]
    if missing:
        raise ValueError(f"Missing blood type columns: {missing}")

    # Ensure no duplicate dates within uploaded file
    if df['date'].duplicated().any():
        raise ValueError('Uploaded dataset contains duplicate date rows.')

    # Keep only date + blood types
    df = df[['date'] + BLOOD_TYPES].copy()
    return df


def merge_with_historical(uploaded_df: pd.DataFrame, historical_path: str = None) -> pd.DataFrame:
    _ensure_dirs()
    # load existing
    candidates = [os.path.join(DATA_DIR, 'download.csv'), os.path.join(DATA_DIR, 'blood_demand_data.csv')]
    existing = None
    for c in candidates:
        if c and os.path.exists(c):
            try:
                existing = pd.read_csv(c)
                existing = _normalize_date_column(existing)
                break
            except Exception:
                continue

    if existing is None:
        existing = pd.DataFrame(columns=['date'] + BLOOD_TYPES)
    else:
        existing = existing[['date'] + BLOOD_TYPES].copy()

    combined = pd.concat([existing, uploaded_df], ignore_index=True)
    combined['date'] = pd.to_datetime(combined['date'])
    # Drop duplicates keeping the first (historical takes precedence)
    combined = combined.sort_values('date')
    combined = combined.drop_duplicates(subset=['date'], keep='first')
    combined = combined.sort_values('date').reset_index(drop=True)

    # Save merged to blood_demand_data.csv
    out_path = os.path.join(DATA_DIR, 'blood_demand_data.csv')
    combined.to_csv(out_path, index=False, date_format='%Y-%m-%d')
    return combined


def train_prophet_models(df: pd.DataFrame) -> Dict:
    _ensure_dirs()
    results = {}
    # For each blood type, train a Prophet model on ds/y format
    for bt in BLOOD_TYPES:
        series = df[['date', bt]].dropna().rename(columns={'date': 'ds', bt: 'y'})
        if series.empty:
            results[bt] = {'status': 'skipped', 'reason': 'no data'}
            continue

        m = Prophet()
        try:
            m.fit(series)
        except Exception as e:
            results[bt] = {'status': 'error', 'error': str(e)}
            continue

        fname = f"prophet_{bt}_model.pkl"
        path = os.path.join(MODEL_DIR, fname)
        with open(path, 'wb') as f:
            pickle.dump(m, f)

        results[bt] = {'status': 'trained', 'path': path}

    return results


def process_and_train(uploaded_path: str, initiated_by: str = 'admin') -> Dict:
    # Update status
    _update_training_status({
        'training_status': 'running',
        'started_at': datetime.utcnow().isoformat(),
        'initiated_by': initiated_by
    })

    try:
        uploaded_df = validate_uploaded_csv(uploaded_path)
        merged = merge_with_historical(uploaded_df)
        trained = train_prophet_models(merged)

        # Build metadata entry
        last_year = int(pd.to_datetime(merged['date']).dt.year.max()) if not merged.empty else datetime.utcnow().year
        records = len(merged)

        meta = _read_metadata()
        # determine version number for this year
        existing_versions = [v for v in meta.get('versions', []) if v.get('model_version', '').startswith(f"{last_year}_v")]
        version_idx = len(existing_versions) + 1
        model_version = f"{last_year}_v{version_idx}"

        entry = {
            'model_version': model_version,
            'trained_on': datetime.utcnow().isoformat(),
            'records': records,
            'trained_results': trained
        }
        meta.setdefault('versions', []).append(entry)
        meta['latest'] = model_version
        _write_metadata(meta)

        _update_training_status({
            'training_status': 'completed',
            'latest_model_version': model_version,
            'last_trained': entry['trained_on'],
            'records': records
        })

        return {'status': 'completed', 'model_version': model_version, 'records': records}
    except Exception as e:
        _update_training_status({
            'training_status': 'failed',
            'error': str(e),
            'failed_at': datetime.utcnow().isoformat()
        })
        raise
