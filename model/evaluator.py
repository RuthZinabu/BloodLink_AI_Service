"""
BloodLink AI - Forecasting Model Evaluator
Computes MAE, RMSE, MAPE, R² via holdout validation and persists results.
"""

import json
import os
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, Tuple

METRICS_PATH = os.path.join("model_files", "metrics.json")

BLOOD_TYPES = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]

MAPE_GRADES = [
    (10,  "Excellent"),
    (20,  "Good"),
    (50,  "Acceptable"),
]


def grade_mape(mape: float) -> str:
    for threshold, label in MAPE_GRADES:
        if mape < threshold:
            return label
    return "Poor"


def compute_regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict:
    """
    Calculate MAE, RMSE, MAPE, and R² between two equal-length arrays.
    MAPE is computed only over non-zero actual values to avoid divide-by-zero.
    """
    actual = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)

    mae = float(np.mean(np.abs(actual - predicted)))
    rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))

    nonzero = actual != 0
    if nonzero.sum() > 0:
        mape = float(
            np.mean(np.abs((actual[nonzero] - predicted[nonzero]) / actual[nonzero])) * 100
        )
    else:
        mape = 0.0

    ss_res = float(np.sum((actual - predicted) ** 2))
    ss_tot = float(np.sum((actual - actual.mean()) ** 2))
    r2 = round(1 - ss_res / ss_tot, 4) if ss_tot > 0 else 0.0

    return {
        "mae":      round(mae,  2),
        "rmse":     round(rmse, 2),
        "mape":     round(mape, 2),
        "r2_score": round(r2,   3),
    }


def _holdout_split(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, object]:
    """
    Split a blood-type-specific DataFrame into train / test by the last
    year-month period present in the data.

    Returns (train_df, test_df, test_period).
    """
    df = df.copy()
    df["year_month"] = pd.to_datetime(df["date"]).dt.to_period("M")
    periods = sorted(df["year_month"].unique())

    if len(periods) < 2:
        return df, pd.DataFrame(), None

    test_period = periods[-1]
    train_df = df[df["year_month"] < test_period]
    test_df  = df[df["year_month"] == test_period]
    return train_df, test_df, test_period


def _seasonal_prediction(
    train_df: pd.DataFrame, test_df: pd.DataFrame
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build a month-level seasonal index from training data and apply it to
    predict each row in test_df.  Returns (actual, predicted) arrays.
    """
    train_df = train_df.copy()
    test_df  = test_df.copy()
    train_df["month"] = pd.to_datetime(train_df["date"]).dt.month
    test_df["month"]  = pd.to_datetime(test_df["date"]).dt.month

    month_avg = (
        train_df.groupby(["blood_type", "component_type", "month"])["demand_units"]
        .mean()
    )
    overall_avg = train_df.groupby(["blood_type", "component_type"])["demand_units"].mean()

    actuals    = []
    predicted  = []

    for _, row in test_df.iterrows():
        bt = row["blood_type"]
        ct = row["component_type"]
        m  = row["month"]

        base = float(overall_avg.get((bt, ct), overall_avg.mean()))
        try:
            seasonal_mean = float(month_avg[(bt, ct, m)])
            overall       = float(overall_avg[(bt, ct)])
            si = seasonal_mean / overall if overall > 0 else 1.0
        except KeyError:
            si = 1.0

        actuals.append(float(row["demand_units"]))
        predicted.append(base * si)

    return np.array(actuals), np.array(predicted)


def evaluate_all_blood_types(df: pd.DataFrame) -> Dict[str, dict]:
    """
    Run holdout evaluation for every blood type and return a per-blood-type
    metrics dictionary.
    """
    results: Dict[str, dict] = {}

    for bt in BLOOD_TYPES:
        bt_df = df[df["blood_type"] == bt].copy()
        if bt_df.empty:
            continue

        train_df, test_df, test_period = _holdout_split(bt_df)

        if test_df.empty or len(test_df) == 0:
            actual    = bt_df["demand_units"].values
            predicted = np.full(len(actual), float(np.mean(actual)))
        else:
            actual, predicted = _seasonal_prediction(train_df, test_df)

        if len(actual) == 0:
            continue

        m = compute_regression_metrics(actual, predicted)
        m["status"]      = grade_mape(m["mape"])
        m["sample_size"] = int(len(bt_df))
        m["test_period"] = str(test_period) if test_period else "N/A"
        results[bt] = m

    return results


def build_metrics_report(df: pd.DataFrame, model_version: Optional[str] = None) -> dict:
    """
    Build the full metrics report dict ready for JSON serialisation or API
    response.
    """
    bt_metrics = evaluate_all_blood_types(df)

    if not bt_metrics:
        return {"error": "No data available to evaluate."}

    mapes  = [v["mape"]  for v in bt_metrics.values()]
    rmses  = [v["rmse"]  for v in bt_metrics.values()]
    maes   = [v["mae"]   for v in bt_metrics.values()]
    r2s    = [v["r2_score"] for v in bt_metrics.values()]

    avg_mape = round(float(np.mean(mapes)),  2)
    avg_rmse = round(float(np.mean(rmses)),  2)
    avg_mae  = round(float(np.mean(maes)),   2)
    avg_r2   = round(float(np.mean(r2s)),    3)

    version = model_version or f"{datetime.today().year}_v1"

    return {
        "model_version": version,
        "last_evaluated": datetime.today().strftime("%Y-%m-%d"),
        "evaluation_method": "holdout_validation",
        "data_description": (
            "Each blood-type model is evaluated by training on all periods except "
            "the most recent month, then predicting that held-out month using a "
            "seasonal index derived from training data."
        ),
        "overall_system_score": {
            "average_mae":  avg_mae,
            "average_rmse": avg_rmse,
            "average_mape": avg_mape,
            "average_r2":   avg_r2,
            "status": grade_mape(avg_mape),
        },
        "grading_scale": {
            "Excellent":  "MAPE < 10%",
            "Good":       "MAPE 10–20%",
            "Acceptable": "MAPE 20–50%",
            "Poor":       "MAPE > 50%",
        },
        "models": bt_metrics,
    }


def save_metrics(report: dict, path: str = METRICS_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(report, f, indent=2)


def load_metrics(path: str = METRICS_PATH) -> Optional[dict]:
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def get_or_compute_metrics(df: pd.DataFrame, force: bool = False) -> dict:
    """
    Load cached metrics from disk if available; otherwise compute, cache,
    and return.  Pass force=True to recompute and overwrite the cache.
    """
    if not force:
        cached = load_metrics()
        if cached:
            return cached

    report = build_metrics_report(df)
    save_metrics(report)
    return report
