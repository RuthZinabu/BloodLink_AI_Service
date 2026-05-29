# BloodLink AI Service — Comprehensive System Documentation

**Version:** 2.0  
**Purpose:** Blood demand forecasting for hospitals and blood banks  
**Stack:** Python · FastAPI · Pandas · NumPy · Prophet (Meta)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Data Foundation](#3-data-foundation)
4. [Forecasting Engine](#4-forecasting-engine)
   - 4.1 Monthly Forecasting
   - 4.2 Yearly Forecasting
   - 4.3 Growth Model
5. [Shortage Prediction](#5-shortage-prediction)
6. [Inventory Integration](#6-inventory-integration)
7. [REST API Reference](#7-rest-api-reference)
8. [Interactive Dashboard](#8-interactive-dashboard)
9. [Configuration & Environment Variables](#9-configuration--environment-variables)
10. [Model Training](#10-model-training)
11. [Data Flow Diagram](#11-data-flow-diagram)
12. [Limitations & Constraints](#12-limitations--constraints)

---

## 1. System Overview

BloodLink AI Service is a forecasting platform that predicts how many units of blood — broken down by **blood type** and **component type** — will be needed in a given hospital or blood bank over the coming months and year. It also compares those predictions against the current inventory to alert staff of impending shortages before they happen.

### What the system predicts

| Dimension | Values |
|---|---|
| **Blood Types (8)** | O+, O−, A+, A−, B+, B−, AB+, AB− |
| **Component Types (5)** | Whole Blood, Packed Red Cells, Fresh Frozen Plasma, Platelets Concentrate, Cryoprecipitate |
| **Total combinations** | 40 (8 × 5) |

Each of the 40 combinations receives its own independent forecast.

### Core capabilities

| Capability | Description |
|---|---|
| **Monthly Forecast** | Predicted demand for each of the next 1–24 months, per combination |
| **Yearly Forecast** | Predicted total annual demand for the next year (projected to 2027) |
| **Shortage Prediction** | Side-by-side comparison of next-month demand vs. live inventory stock |
| **REST API** | JSON endpoints usable by any frontend or external system |
| **Interactive Dashboard** | Browser-based charts and matrix tables |

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     dashboard.html                           │
│              (Browser — Chart.js UI)                         │
└────────────────────────┬─────────────────────────────────────┘
                         │  HTTP (relative URLs)
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                   api/main.py  (FastAPI)                     │
│   GET /               → serves dashboard.html                │
│   GET /forecast/monthly                                      │
│   GET /forecast/yearly                                       │
│   GET /forecast/shortages                                    │
│   GET /forecast/blood-types                                  │
│   GET /forecast/component-types                              │
│   GET /forecast/info                                         │
└────────┬───────────────────────────────────────┬─────────────┘
         │                                       │
         ▼                                       ▼
┌─────────────────────┐              ┌───────────────────────┐
│ model/              │              │ model/                │
│ forecast_generator  │              │ inventory_client.py   │
│ .py                 │              │                       │
│                     │              │  Authenticates to the │
│  MonthlyForecast    │              │  external BloodLink   │
│  Generator          │              │  backend API and      │
│                     │              │  fetches live stock   │
│  YearlyForecast     │              │  levels               │
│  Generator          │              └───────────────────────┘
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ data/               │
│ simulation_data_    │
│ with_components.csv │
│ (historical demand) │
└─────────────────────┘
```

### Key files

| File | Role |
|---|---|
| `api/main.py` | FastAPI application — defines all HTTP endpoints, initialises generators |
| `model/forecast_generator.py` | Core forecasting logic — `MonthlyForecastGenerator`, `YearlyForecastGenerator`, `SimulationDataLoader` |
| `model/inventory_client.py` | HTTP client that authenticates and queries the live inventory backend |
| `model/data_loader.py` | Alternative CSV loader for Prophet-compatible time-series data |
| `model/predictor.py` | Prophet model inference helper (legacy, used by training pipeline) |
| `model/holiday_data.py` | Ethiopian public holiday definitions for Prophet models |
| `data/simulation_data_with_components.csv` | Historical demand dataset used by the forecast generators |
| `data/blood_demand_data.csv` | Fallback historical dataset |
| `model_files/` | Serialised (pickle) Prophet models — one per blood type |
| `train_models.py` | Script to re-train Prophet models against new real-world data |
| `dashboard.html` | Single-file frontend served at `/` |
| `start.sh` | Startup script — runs `uvicorn` on port 5000 |

---

## 3. Data Foundation

### 3.1 Historical demand dataset

The forecasting engine reads from CSV files in the `data/` directory. The system tries the following paths in order:

1. `data/download.csv` — real blood bank export (preferred)
2. `data/simulation_data_with_components.csv` — bundled simulation data (fallback)

The required columns are:

| Column | Type | Example |
|---|---|---|
| `date` | Date string | `2023-01-01` |
| `blood_type` | String | `O+` |
| `component_type` | String | `Packed Red Cells` |
| `demand_units` | Integer | `12` |

Each row represents the total demand for one blood-type/component combination on one date.

### 3.2 Updating with real data

To replace the simulation data with real blood bank records:

1. Export your demand records to a CSV matching the column structure above.
2. Save it as `data/download.csv`.
3. Restart the service — the `SimulationDataLoader` automatically detects and loads it on startup.

No code changes are required. The forecasting algorithms adapt to whatever historical window is present in the file.

---

## 4. Forecasting Engine

The engine lives entirely in `model/forecast_generator.py` and contains three classes:

| Class | Purpose |
|---|---|
| `SimulationDataLoader` | Reads and validates the CSV dataset |
| `MonthlyForecastGenerator` | Produces month-by-month predictions |
| `YearlyForecastGenerator` | Produces annual totals for the next year |

Both generator classes are instantiated **once at API startup** in `api/main.py`:

```python
monthly_gen = MonthlyForecastGenerator()
yearly_gen  = YearlyForecastGenerator()
```

This means the CSV is loaded into memory when the server starts — requests are fast because no disk I/O happens during forecasting.

---

### 4.1 Monthly Forecasting

**Goal:** For each of the 40 blood-type/component combinations, predict how many units will be needed in each of the next N months (up to 24).

#### Step-by-step algorithm

**Step 1 — Data preparation**

On startup, the CSV is loaded into a Pandas DataFrame. Extra columns are derived:

```
year       →  extracted from date
month      →  1–12
month_name →  "January", "February", ...
year_month →  pandas Period (YYYY-MM)
```

**Step 2 — Grouping**

The data is grouped by `(year_month, blood_type, component_type)` and the `demand_units` are summed. This gives monthly totals for every combination.

**Step 3 — Seasonal profile construction**

For each combination, a **monthly seasonal index** is calculated:

```
seasonal_index[month] = average_demand_in_that_month / overall_average_demand
```

This captures whether, for example, O+ Packed Red Cells tend to spike in March and dip in August. If a month has no data, its index defaults to 1.0 (no seasonal adjustment).

**Step 4 — Base demand**

The base monthly demand for each combination is taken from the **last year present in the data**:

```
base_demand = mean of all monthly values in the most recent year
```

If there is only one year of data, the overall mean is used.

**Step 5 — Forecast generation**

For each future month `i` (starting from the current month):

```
month_factor  = seasonal_index[target_month]
growth_factor = (1 + 0.08) ^ (i / 12)      ← continuous 8% annual growth

predicted_units = round(base_demand × month_factor × growth_factor)
```

This applies both the seasonal shape (which months are historically busier) and a steady upward growth trend.

**Step 6 — Ceiling constraint**

Forecasts are capped at the end of 2027:

```python
MAX_FORECAST_YEAR = 2027
```

Any request for months beyond December 2027 returns an empty list.

#### Example output (one combination)

```json
{
  "blood_type": "O+",
  "component_type": "Packed Red Cells",
  "month": 6,
  "month_name": "June",
  "year": 2027,
  "predicted_units": 134
}
```

---

### 4.2 Yearly Forecasting

**Goal:** Predict the total annual demand for each of the 40 combinations for the next year (always `current_year + 1`, i.e. 2027 as of 2026).

#### Step-by-step algorithm

**Step 1 — Aggregate yearly totals**

Monthly records are summed to produce yearly totals per combination:

```
yearly_demand[year][blood_type][component_type] = sum of all monthly demand_units
```

**Step 2 — Identify the historical baseline**

The most recent year present in the data is used as the baseline:

```
baseline_year   = max year in data  (e.g. 2023)
baseline_demand = total units for that year
```

**Step 3 — Compound growth projection**

The target year is always `current_year + 1` (anchored to today's date, not the data):

```
target_year         = datetime.today().year + 1          (e.g. 2027)
years_from_baseline = target_year − baseline_year        (e.g. 4)

predicted_units = baseline_demand × (1.08) ^ years_from_baseline
```

This means that even if the historical data only goes up to 2023, the system correctly projects forward to 2027 using 4 years of compound growth — rather than showing 2024 (which would happen if it naively added 1 to the data's last year).

#### Example output (one combination)

```json
{
  "blood_type": "A-",
  "component_type": "Whole Blood",
  "year": 2027,
  "predicted_units": 2187,
  "growth_rate": 0.08
}
```

---

### 4.3 Growth Model

Both monthly and yearly forecasting apply an **8% annual growth rate**. This value is derived from observed trends in blood demand at Ethiopian blood banks and is configurable via the `DEFAULT_GROWTH_RATE` constant in `forecast_generator.py`.

The rationale for 8%:
- Population growth in the service area
- Increasing hospital admission rates
- Expanded surgical capacity over time

To change the growth rate, update this constant and restart the service:

```python
# model/forecast_generator.py, line 25
DEFAULT_GROWTH_RATE = 0.08  # change to e.g. 0.06 for 6%
```

---

## 5. Shortage Prediction

The shortage endpoint (`GET /forecast/shortages`) compares next month's predicted demand against what is currently in the blood bank inventory.

### Algorithm

**Step 1 — Determine target month**

```
today           = current date
forecast_month  = today.month + 1  (wraps to January if December)
forecast_year   = today.year       (or today.year + 1 if wrapping)
```

**Step 2 — Generate demand forecast**

The monthly forecast generator is called with `months_ahead=1` starting at the target month. This produces predicted units for all 40 combinations.

**Step 3 — Fetch live stock**

The inventory client authenticates to the external BloodLink backend and fetches current available stock, broken down by blood type **and** component type.

**Step 4 — Compute shortage**

For each of the 40 combinations:

```
shortage = max(0, predicted_demand − available_stock)
```

A shortage of zero means supply is adequate. A positive number is the deficit (units that need to be sourced).

### Response structure

```json
{
  "status": "success",
  "forecast_month": 6,
  "forecast_year": 2026,
  "predicted_by_blood_type": { "O+": 450, "A+": 380, ... },
  "predicted_by_component":  { "Packed Red Cells": 600, ... },
  "predicted_by_blood_and_component": {
    "O+": { "Packed Red Cells": 120, "Whole Blood": 80, ... },
    ...
  },
  "available_by_blood_and_component": {
    "O+": { "Packed Red Cells": 95, "Whole Blood": 100, ... },
    ...
  },
  "shortage_by_blood_and_component": {
    "O+": { "Packed Red Cells": 25, "Whole Blood": 0, ... },
    ...
  },
  "shortages": [
    {
      "blood_type": "O+",
      "component_type": "Packed Red Cells",
      "predicted_demand": 120,
      "available_stock": 95,
      "shortage": 25
    }
  ],
  "inventory_source": "https://bloodlink-backend-bpll.onrender.com"
}
```

### Dashboard display

The dashboard renders the shortage response as **three pivot matrix tables**, each with component types as rows and blood types as columns:

| Table | Content |
|---|---|
| Predicted Demand | Units forecast per cell |
| Available Stock | Current inventory per cell |
| Shortage | Deficit per cell — highlighted red if > 0, green if 0 |

---

## 6. Inventory Integration

The `model/inventory_client.py` module handles all communication with the external BloodLink inventory backend.

### Authentication

The client uses **admin credential login** (email + password) to obtain a JWT bearer token:

```
POST {INVENTORY_API_BASE_URL}/api/auth/login
     { "email": "...", "password": "..." }
     → { "access_token": "eyJ..." }
```

The token is then used as a `Authorization: Bearer <token>` header on all subsequent requests.

### Inventory fetch

```
GET {INVENTORY_API_BASE_URL}/api/inventory
    Authorization: Bearer <token>
```

The response is normalised to the internal format regardless of what the backend returns. The client handles two response shapes:

1. **Pre-aggregated** — backend returns `{ "by_blood_and_component": { "O+_PRBC": 95, ... } }`
2. **Unit-level list** — backend returns a list of individual blood unit objects, which the client aggregates itself, filtering only `status = "AVAILABLE"` units

Component codes from the backend (e.g. `PRBC`, `WHOLE_BLOOD`, `PLASMA`) are mapped to the system's display names:

| Backend code | Display name |
|---|---|
| `PRBC` | Packed Red Cells |
| `WHOLE_BLOOD` | Whole Blood |
| `PLASMA` | Fresh Frozen Plasma |
| `CRYOPRECIPITATE` | Cryoprecipitate |
| `PLATELETS` | Platelets Concentrate |

### Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `INVENTORY_API_BASE_URL` | `https://bloodlink-backend-bpll.onrender.com` | Base URL of the inventory backend |
| `INVENTORY_ADMIN_EMAIL` | `admin@bloodlink.com` | Admin login email |
| `INVENTORY_ADMIN_PASSWORD` | `Admin123!` | Admin login password |

---

## 7. REST API Reference

### Base URL

Development: `http://localhost:5000`  
Production: your `.replit.app` domain (or custom domain)

### Endpoints

#### `GET /`
Returns the interactive dashboard HTML page.

---

#### `GET /forecast/monthly`

Returns month-by-month demand predictions.

**Query parameters:**

| Parameter | Type | Default | Range | Description |
|---|---|---|---|---|
| `blood_type` | string | (all) | O+, O−, A+, A−, B+, B−, AB+, AB− | Filter to one blood type |
| `component_type` | string | (all) | See component list | Filter to one component |
| `months_ahead` | integer | 12 | 1–24 | How many months to predict |

**Example:**
```
GET /forecast/monthly?blood_type=O%2B&component_type=Whole%20Blood&months_ahead=6
```

**Response:**
```json
{
  "status": "success",
  "forecast_type": "monthly",
  "filters": { "blood_type": "O+", "component_type": "Whole Blood" },
  "months_ahead": 6,
  "data": [
    {
      "blood_type": "O+",
      "component_type": "Whole Blood",
      "month": 6,
      "month_name": "June",
      "year": 2026,
      "predicted_units": 110
    }
  ]
}
```

---

#### `GET /forecast/yearly`

Returns annual total demand predictions anchored to the next calendar year.

**Query parameters:**

| Parameter | Type | Default | Range | Description |
|---|---|---|---|---|
| `blood_type` | string | (all) | — | Filter to one blood type |
| `component_type` | string | (all) | — | Filter to one component |
| `years_ahead` | integer | 1 | 1–10 | How many years ahead (default and recommended: 1) |

**Example:**
```
GET /forecast/yearly?blood_type=A-
```

**Response:**
```json
{
  "status": "success",
  "forecast_type": "yearly",
  "filters": { "blood_type": "A-", "component_type": null },
  "years_ahead": 1,
  "growth_rate": 0.08,
  "data": [
    {
      "blood_type": "A-",
      "component_type": "Whole Blood",
      "year": 2027,
      "predicted_units": 2187,
      "growth_rate": 0.08
    }
  ]
}
```

---

#### `GET /forecast/shortages`

Returns shortage risk for the next calendar month.

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `blood_type` | string | (all) | Filter to one blood type |
| `component_type` | string | (all) | Filter to one component |

---

#### `GET /forecast/blood-types`

Returns the list of supported blood types.

#### `GET /forecast/component-types`

Returns the list of supported component types.

#### `GET /forecast/info`

Returns metadata about all forecasting capabilities and their parameters.

#### `GET /docs`

Interactive Swagger UI — explore and test all endpoints in the browser.

---

## 8. Interactive Dashboard

The dashboard (`dashboard.html`) is a single HTML file served directly by the FastAPI app. It requires no build step.

### Panels

| Panel | Function |
|---|---|
| **Monthly Forecast** | Select blood type, component, and months ahead; renders a multi-line Chart.js chart |
| **Yearly Forecast** | Select blood type and component; renders a bar chart for 2027 |
| **Shortage Prediction** | Select optional filters; loads three matrix tables comparing predicted vs. available vs. shortage |
| **API Information** | Quick-reference for all endpoints and example queries |

### Monthly forecast chart

- One line per blood-type/component combination (up to 40 lines when unfiltered)
- X-axis: month labels (`June 2026`, `July 2026`, …)
- Y-axis: predicted units
- Uses Chart.js with a randomly assigned colour per combination

### Yearly forecast chart

- Bar chart, one bar per combination
- X-axis: blood-type + component label
- Y-axis: predicted units for the forecast year (2027)

### Shortage matrix tables

Three stacked tables, each with the layout:

```
┌─────────────────────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┐
│ COMPONENT TYPE      │  A+  │  A−  │  B+  │  B−  │ AB+  │ AB−  │  O+  │  O−  │
├─────────────────────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┤
│ Whole Blood         │  --  │  --  │  --  │  --  │  --  │  --  │  --  │  --  │
│ Packed Red Cells    │  --  │  --  │  --  │  --  │  --  │  --  │  --  │  --  │
│ Fresh Frozen Plasma │  --  │  --  │  --  │  --  │  --  │  --  │  --  │  --  │
│ Platelets Conc.     │  --  │  --  │  --  │  --  │  --  │  --  │  --  │  --  │
│ Cryoprecipitate     │  --  │  --  │  --  │  --  │  --  │  --  │  --  │  --  │
└─────────────────────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┘
```

In the **Shortage** table, cells with a value greater than zero are highlighted red; zeros are shown in green.

---

## 9. Configuration & Environment Variables

| Variable | Default | Description |
|---|---|---|
| `INVENTORY_API_BASE_URL` | `https://bloodlink-backend-bpll.onrender.com` | URL of the external inventory backend |
| `INVENTORY_ADMIN_EMAIL` | `admin@bloodlink.com` | Admin email for inventory authentication |
| `INVENTORY_ADMIN_PASSWORD` | `Admin123!` | Admin password for inventory authentication |

The application listens on **port 5000** (hardcoded in `start.sh`).

---

## 10. Model Training

The system includes Prophet-based models trained per blood type for higher-accuracy predictions. These are serialised to `.pkl` files in `model_files/`.

### What is Prophet?

Prophet (by Meta/Facebook) is a time-series forecasting library designed for data with strong seasonal patterns and holiday effects. It decomposes a time series into:

- **Trend** — long-term growth or decline
- **Seasonality** — yearly and weekly cycles
- **Holidays** — special calendar events that cause demand spikes or dips

### Holiday integration

Ethiopian public holidays are defined in `model/holiday_data.py` and injected into each Prophet model as regressors. This allows the model to learn, for example, that demand spikes before major holidays such as Ethiopian Christmas (January 7) or Timkat (January 19).

### Training a model

1. Place real blood bank demand data at `data/download.csv`.
2. Run:
   ```bash
   python train_models.py
   ```
3. Trained models are saved to `model_files/`. Restart the service to use them.

### Model configuration (from `notebooks/blood_forecast_model.ipynb`)

| Setting | Value |
|---|---|
| Yearly seasonality | Enabled |
| Weekly seasonality | Enabled |
| Daily seasonality | Disabled |
| Holiday window | ±1 day around each holiday |
| Separate model per | Blood type |

---

## 11. Data Flow Diagram

```
User opens dashboard
        │
        ▼
Browser fetches GET /
        │
        ▼
FastAPI returns dashboard.html
        │
        ▼
JavaScript calls GET /forecast/monthly   ──────────────────────────┐
                 GET /forecast/yearly    ──────────────────────────┤
                 GET /forecast/shortages ──────────────────────────┤
                                                                    │
                                                                    ▼
                                                        ┌───────────────────┐
                                                        │  FastAPI handler  │
                                                        └────────┬──────────┘
                                                                 │
                              ┌──────────────────────────────────┼──────────────────────────┐
                              │                                  │                          │
                              ▼                                  ▼                          ▼
                   MonthlyForecastGenerator        YearlyForecastGenerator       inventory_client
                              │                                  │                          │
                              ▼                                  ▼                          ▼
                    Load CSV data                      Load CSV data            POST /api/auth/login
                    Group by month                     Group by year            GET /api/inventory
                    Compute seasonal index             Identify baseline        Normalise component codes
                    Apply growth factor                Apply compound growth    Return breakdown dict
                    Return forecast list               Return forecast list
                              │                                  │                          │
                              └──────────────────────────────────┴──────────────────────────┘
                                                                 │
                                                                 ▼
                                                       JSON response to browser
                                                                 │
                                                                 ▼
                                                  Chart.js renders charts
                                                  Matrix tables rendered for shortages
```

---

## 12. Limitations & Constraints

| Constraint | Detail |
|---|---|
| **Forecast horizon** | Predictions are capped at December 2027 (`MAX_FORECAST_YEAR = 2027`). Requests beyond this return an empty dataset. |
| **Historical data depth** | The current bundled dataset covers only January–March 2023. A richer dataset will improve seasonal accuracy significantly. |
| **Growth rate is fixed** | The 8% annual growth rate is a constant, not a dynamically learned value. If actual demand trends diverge from 8%, accuracy will degrade over time. |
| **No real-time updates** | The forecast generators load data once at startup. New CSV data requires a server restart to take effect. |
| **Inventory connectivity** | The shortage prediction requires a live connection to the external BloodLink backend. If that service is unreachable, shortage data is unavailable. |
| **No per-facility model** | All forecasts represent aggregate demand. There is no facility-level segmentation. |
| **Shortage month scope** | Shortage prediction only covers the next calendar month — not multiple months ahead. |
| **Prophet models** | The serialised Prophet models in `model_files/` are pre-trained. They do not update automatically as new data arrives. Re-training requires running `train_models.py` manually. |

---

*Document prepared for BloodLink AI Service v2.0 — May 2026*
