# BloodLink AI — Model Evaluation Metrics

**Feature added:** May 2026  
**Module:** `model/evaluator.py`  
**Endpoints:** `GET /model/metrics`, `GET /model/metrics/{blood_type}`, `POST /model/metrics/refresh`

---

## Overview

The model evaluation subsystem measures and exposes the **accuracy and reliability** of every blood-demand forecasting model in BloodLink AI. It applies industry-standard regression metrics — MAE, RMSE, MAPE, and R² — to quantify how well the system predicts real demand, and grades each model using a MAPE-based scale aligned with healthcare forecasting standards.

Metrics are computed automatically at service startup, persisted to disk, and re-exposed through dedicated API endpoints. Any connected frontend, monitoring system, or audit report can consume them without running a separate evaluation pipeline.

---

## Evaluation Methodology

### Holdout Validation

Each blood-type model is evaluated independently using a **time-series holdout split**:

```
All historical periods
│
├── Training set  →  all months except the most recent
└── Test set      →  the most recent month only
```

**Why holdout?**  
Holdout validation simulates real-world forecasting: the model is trained on everything it would have known at a point in the past, then asked to predict the next period it has never seen. This avoids data leakage and gives an honest measure of out-of-sample accuracy.

### Prediction Method

For the test month, the evaluator generates predictions using the same seasonal-index approach the live API uses:

1. Compute the mean demand per month from the training period.
2. Divide each monthly mean by the overall training mean to get a **seasonal index** per (blood type, component type, month).
3. Multiply the overall training mean by the test month's seasonal index to produce the prediction.
4. Compare predicted values to the actual test-period values row by row.

### Aggregation

Metrics for each blood type are averaged across all 5 component types (`Whole Blood`, `Packed Red Cells`, `Fresh Frozen Plasma`, `Platelets Concentrate`, `Cryoprecipitate`).  
The **overall system score** is the average of all 8 blood-type scores.

---

## Metrics Reference

| Metric | Formula | Interpretation |
|---|---|---|
| **MAE** | `mean(|actual − predicted|)` | Average absolute error in units. Lower is better. |
| **RMSE** | `sqrt(mean((actual − predicted)²))` | Penalises large errors more than MAE. Lower is better. |
| **MAPE** | `mean(|actual − predicted| / actual) × 100` | Error as a percentage of actual demand. Lower is better. Calculated only over non-zero actuals to avoid divide-by-zero. |
| **R²** | `1 − (SS_res / SS_tot)` | Proportion of variance explained. 1.0 = perfect; 0 = no better than the mean; negative = worse than the mean. |

---

## Grading Scale

Each model is graded based on its **MAPE** value, following accepted standards in healthcare and supply-chain forecasting:

| Grade | MAPE Threshold | Meaning |
|---|---|---|
| **Excellent** | < 10% | Highly reliable; suitable for direct operational decisions |
| **Good** | 10% – 20% | Reliable for planning; minor manual review recommended |
| **Acceptable** | 20% – 50% | Useful as a directional guide; supplement with domain expertise |
| **Poor** | > 50% | Model needs more historical data or retraining before use |

The same grade is applied to individual blood-type models and to the overall system score.

---

## API Endpoints

### `GET /model/metrics`

Returns evaluation metrics for all 8 blood-type models plus the global system score.

**Response example:**

```json
{
  "model_version": "2026_v1",
  "last_evaluated": "2026-05-30",
  "evaluation_method": "holdout_validation",
  "data_description": "Each blood-type model is evaluated by training on all periods except the most recent month, then predicting that held-out month using a seasonal index derived from training data.",
  "overall_system_score": {
    "average_mae": 38.87,
    "average_rmse": 45.27,
    "average_mape": 67.93,
    "average_r2": -0.725,
    "status": "Acceptable"
  },
  "grading_scale": {
    "Excellent": "MAPE < 10%",
    "Good": "MAPE 10–20%",
    "Acceptable": "MAPE 20–50%",
    "Poor": "MAPE > 50%"
  },
  "models": {
    "O+": {
      "mae": 122.6,
      "rmse": 142.48,
      "mape": 65.19,
      "r2_score": -0.608,
      "status": "Acceptable",
      "sample_size": 20,
      "test_period": "2023-03"
    },
    "A+": {
      "mae": 111.87,
      "rmse": 130.77,
      "mape": 65.55,
      "r2_score": -0.559,
      "status": "Poor",
      "sample_size": 20,
      "test_period": "2023-03"
    }
  }
}
```

---

### `GET /model/metrics/{blood_type}`

Returns metrics for a single blood type.

**Path parameter:** `blood_type` — URL-encoded blood type string.

| Blood type | URL |
|---|---|
| O+ | `/model/metrics/O%2B` |
| O− | `/model/metrics/O-` |
| A+ | `/model/metrics/A%2B` |
| AB− | `/model/metrics/AB-` |

**Example request:**
```
GET /model/metrics/O%2B
```

**Response example:**
```json
{
  "model_version": "2026_v1",
  "last_evaluated": "2026-05-30",
  "evaluation_method": "holdout_validation",
  "blood_type": "O+",
  "mae": 122.6,
  "rmse": 142.48,
  "mape": 65.19,
  "r2_score": -0.608,
  "evaluation_status": "Acceptable",
  "sample_size": 20,
  "test_period": "2023-03",
  "grading_scale": {
    "Excellent": "MAPE < 10%",
    "Good": "MAPE 10–20%",
    "Acceptable": "MAPE 20–50%",
    "Poor": "MAPE > 50%"
  }
}
```

**Error responses:**

| Code | Reason |
|---|---|
| `404` | Blood type not recognised or no metrics available for that type |

---

### `POST /model/metrics/refresh`

Forces a full recomputation of all metrics from the current dataset and overwrites the on-disk cache.

**When to call this:**
- After uploading a new or updated `data/download.csv`
- After retraining models with `python train_models.py`
- On demand to ensure metrics reflect the latest data

**Request:** No body required.

**Response example:**
```json
{
  "status": "refreshed",
  "metrics": { ... }
}
```

---

## Swagger / OpenAPI

All three endpoints are tagged **Model Metrics** in the interactive Swagger UI.  
Visit `/docs` on the running service to explore and test them directly in the browser.

---

## Implementation Details

### File: `model/evaluator.py`

| Function | Purpose |
|---|---|
| `compute_regression_metrics(actual, predicted)` | Core metric computation — returns MAE, RMSE, MAPE, R² |
| `grade_mape(mape)` | Maps a MAPE value to its grade string |
| `evaluate_all_blood_types(df)` | Runs holdout evaluation for all 8 blood types |
| `build_metrics_report(df)` | Assembles the full JSON-ready report |
| `save_metrics(report)` | Writes report to `model_files/metrics.json` |
| `load_metrics()` | Reads and returns the cached report from disk |
| `get_or_compute_metrics(df, force)` | Load from cache if available; compute and cache otherwise |

### Caching

Metrics are stored at `model_files/metrics.json`. On startup, `api/main.py` calls `get_or_compute_metrics()`:

- If `metrics.json` exists → loaded instantly (no recomputation cost)
- If missing → computed, saved to disk, and served

This means server restarts do not re-run evaluation unless the cache file is deleted or `POST /model/metrics/refresh` is called.

### Integration in `api/main.py`

```python
# Startup — runs once
_demand_df    = SimulationDataLoader.load_simulation_data()
_metrics_cache = get_or_compute_metrics(_demand_df)
```

The `_metrics_cache` dict is kept in module-level memory and returned directly by the GET endpoints. The `refresh` endpoint updates both the in-memory cache and the disk file.

---

*Part of BloodLink AI Service v2.0 — Model Evaluation Subsystem*
