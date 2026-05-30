import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from model.forecast_generator import MonthlyForecastGenerator, YearlyForecastGenerator, SimulationDataLoader
from model.inventory_client import fetch_inventory_stock, fetch_inventory_breakdown, InventoryIntegrationError
from model.evaluator import get_or_compute_metrics, build_metrics_report, save_metrics, BLOOD_TYPES
from typing import Optional, List

INVENTORY_API_BASE_URL = os.environ.get(
    'INVENTORY_API_BASE_URL',
    'https://bloodlink-backend-bpll.onrender.com'
)

app = FastAPI(
    title="Blood Demand Forecast API",
    description="Monthly and Yearly blood demand forecasting by blood type and component type",
    version="2.0.0"
)

# Allow CORS (for your React frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize forecast generators
monthly_gen = MonthlyForecastGenerator()
yearly_gen = YearlyForecastGenerator()

# Load (or compute and cache) model evaluation metrics at startup
_demand_df = SimulationDataLoader.load_simulation_data()
_metrics_cache: dict = get_or_compute_metrics(_demand_df)

@app.get("/", response_class=HTMLResponse)
def home():
    dashboard_path = Path(__file__).parent.parent / "dashboard.html"
    if dashboard_path.exists():
        return HTMLResponse(content=dashboard_path.read_text())
    return HTMLResponse(content="<h1>Blood Demand Forecast API is running</h1><p>Visit <a href='/docs'>/docs</a> for the API documentation.</p>")

# ========================================
# Monthly Forecast Endpoints
# ========================================

@app.get("/forecast/monthly")
def forecast_monthly(
    blood_type: Optional[str] = Query(None, description="Filter by blood type (e.g., O+, A-, B+, AB+, etc.)"),
    component_type: Optional[str] = Query(None, description="Filter by component type (e.g., Whole Blood, Packed Red Cells, etc.)"),
    months_ahead: int = Query(12, ge=1, le=24, description="Number of months to forecast (1-24, default 12)")
):
    """
    Return monthly blood demand forecast grouped by blood type and component type.
    
    Query Parameters:
    - blood_type: Optional filter by blood type
    - component_type: Optional filter by component type
    - months_ahead: Number of months to forecast (1-24, default 12)
    
    Response format:
    [
        {
            "blood_type": "O+",
            "component_type": "Packed Red Cells",
            "month": 6,
            "month_name": "June",
            "year": 2026,
            "predicted_units": 120
        },
        ...
    ]
    """
    try:
        forecast_data = monthly_gen.get_monthly_forecast(
            blood_type=blood_type,
            component_type=component_type,
            months_ahead=months_ahead
        )
        return {
            "status": "success",
            "forecast_type": "monthly",
            "filters": {
                "blood_type": blood_type,
                "component_type": component_type
            },
            "months_ahead": months_ahead,
            "data": forecast_data
        }
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e)
        }

# ========================================
# Shortage Prediction Endpoint
# ========================================

@app.get("/forecast/shortages")
def forecast_shortages(
    blood_type: Optional[str] = Query(None, description="Filter by blood type for shortage estimation"),
    component_type: Optional[str] = Query(None, description="Filter by component type for shortage estimation")
):
    """
    Predict blood shortages for the next calendar month by comparing forecast demand to current inventory.
    """
    today = datetime.today()
    next_month = today.month + 1
    next_year = today.year
    if next_month > 12:
        next_month = 1
        next_year += 1

    if next_year > 2027:
        return {
            "status": "error",
            "message": "Shortage predictions are limited to end of year 2027."
        }

    try:
        forecast_data = monthly_gen.get_monthly_forecast(
            blood_type=blood_type,
            component_type=component_type,
            months_ahead=1,
            start_year=next_year,
            start_month=next_month
        )

        if not forecast_data:
            return {
                "status": "success",
                "forecast_month": next_month,
                "forecast_year": next_year,
                "current_stock": {},
                "shortages": [],
                "message": "No forecast data available for next month."
            }

        stock = fetch_inventory_breakdown(base_url=INVENTORY_API_BASE_URL)
        demand_by_blood_type = {}
        demand_by_component = {}
        demand_by_blood_and_component = {}

        for record in forecast_data:
            bt = record['blood_type']
            ct = record['component_type']
            units = record['predicted_units']
            demand_by_blood_type[bt] = demand_by_blood_type.get(bt, 0) + units
            demand_by_component[ct] = demand_by_component.get(ct, 0) + units
            blood_components = demand_by_blood_and_component.setdefault(bt, {})
            blood_components[ct] = blood_components.get(ct, 0) + units

        shortages = []
        shortage_by_blood_and_component = {}
        all_blood_types = set(list(demand_by_blood_and_component.keys()) + list(stock.keys()))

        for bt in all_blood_types:
            demand_components = demand_by_blood_and_component.get(bt, {})
            available_components = stock.get(bt, {})
            shortage_components = {}

            all_components = set(list(demand_components.keys()) + list(available_components.keys()))
            for ct in all_components:
                predicted = demand_components.get(ct, 0)
                available = available_components.get(ct, 0)
                shortage = max(0, predicted - available)
                shortage_components[ct] = shortage

                if predicted > 0 or available > 0:
                    shortages.append({
                        'blood_type': bt,
                        'component_type': ct,
                        'predicted_demand': predicted,
                        'available_stock': available,
                        'shortage': shortage
                    })

            shortage_by_blood_and_component[bt] = shortage_components

        return {
            "status": "success",
            "forecast_month": next_month,
            "forecast_year": next_year,
            "filters": {
                "blood_type": blood_type,
                "component_type": component_type
            },
            "predicted_by_blood_type": demand_by_blood_type,
            "predicted_by_component": demand_by_component,
            "predicted_by_blood_and_component": demand_by_blood_and_component,
            "available_by_blood_and_component": stock,
            "shortage_by_blood_and_component": shortage_by_blood_and_component,
            "shortages": shortages,
            "inventory_source": INVENTORY_API_BASE_URL
        }
    except InventoryIntegrationError as e:
        return {
            "status": "error",
            "message": str(e)
        }
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e)
        }

# ========================================
# Yearly Forecast Endpoints
# ========================================

@app.get("/forecast/yearly")
def forecast_yearly(
    blood_type: Optional[str] = Query(None, description="Filter by blood type (e.g., O+, A-, B+, AB+, etc.)"),
    component_type: Optional[str] = Query(None, description="Filter by component type (e.g., Whole Blood, Packed Red Cells, etc.)"),
    years_ahead: int = Query(1, ge=1, le=10, description="Number of years to forecast (1-10, default 1)")
):
    """
    Return yearly blood demand forecast using trend-based projection.
    Groups by blood type and component type with configurable growth rate.
    
    Query Parameters:
    - blood_type: Optional filter by blood type
    - component_type: Optional filter by component type
    - years_ahead: Number of years to forecast (1-10, default 3)
    
    Response format:
    [
        {
            "blood_type": "O+",
            "component_type": "Whole Blood",
            "year": 2027,
            "predicted_units": 3456,
            "growth_rate": 0.08
        },
        ...
    ]
    """
    try:
        forecast_data = yearly_gen.get_yearly_forecast(
            blood_type=blood_type,
            component_type=component_type,
            years_ahead=years_ahead
        )
        return {
            "status": "success",
            "forecast_type": "yearly",
            "filters": {
                "blood_type": blood_type,
                "component_type": component_type
            },
            "years_ahead": years_ahead,
            "growth_rate": yearly_gen.growth_rate,
            "data": forecast_data
        }
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e)
        }

# ========================================
# Metadata Endpoints
# ========================================

@app.get("/forecast/blood-types")
def get_blood_types():
    """Return list of available blood types"""
    return {
        "blood_types": [
            "O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"
        ]
    }

@app.get("/forecast/component-types")
def get_component_types():
    """Return list of available component types"""
    return {
        "component_types": [
            "Whole Blood",
            "Packed Red Cells",
            "Fresh Frozen Plasma",
            "Platelets Concentrate",
            "Cryoprecipitate"
        ]
    }

@app.get("/forecast/info")
def get_forecast_info():
    """Return information about available forecasting options"""
    return {
        "forecasting_capabilities": {
            "monthly_forecast": {
                "description": "Monthly demand forecast grouped by blood type and component type",
                "max_months": 24,
                "default_months": 12,
                "filters": ["blood_type", "component_type"]
            },
            "yearly_forecast": {
                "description": "Yearly demand forecast using trend-based projection (8% default growth rate)",
                "max_years": 10,
                "default_years": 3,
                "filters": ["blood_type", "component_type"],
                "growth_rate": 0.08
            }
        },
        "blood_types": ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"],
        "component_types": [
            "Whole Blood",
            "Packed Red Cells",
            "Fresh Frozen Plasma",
            "Platelets Concentrate",
            "Cryoprecipitate"
        ]
    }


# ========================================
# Model Metrics Endpoints
# ========================================

@app.get(
    "/model/metrics",
    summary="Global model evaluation metrics",
    tags=["Model Metrics"],
    response_description=(
        "MAE, RMSE, MAPE and R² for every blood-type model, plus an "
        "overall system performance score."
    ),
)
def get_all_metrics():
    """
    Return forecasting evaluation metrics for all blood-type models.

    Metrics are computed via **holdout validation**: all periods except the
    most recent month are used for training; predictions for that held-out
    month are compared against actuals.

    ### Grading scale (based on MAPE)
    | Grade      | MAPE         |
    |------------|--------------|
    | Excellent  | < 10 %       |
    | Good       | 10 – 20 %    |
    | Acceptable | 20 – 50 %    |
    | Poor       | > 50 %       |
    """
    return _metrics_cache


@app.get(
    "/model/metrics/{blood_type}",
    summary="Per-blood-type model evaluation metrics",
    tags=["Model Metrics"],
    response_description="MAE, RMSE, MAPE, R² and evaluation status for one blood type.",
)
def get_metrics_for_blood_type(blood_type: str):
    """
    Return forecasting evaluation metrics for a specific blood type.

    **Path parameter:** `blood_type` — one of O+, O−, A+, A−, B+, B−, AB+, AB−

    Example: `GET /model/metrics/O+`
    """
    valid_types = [bt.replace("+", "%2B") for bt in BLOOD_TYPES] + BLOOD_TYPES
    if blood_type not in BLOOD_TYPES:
        raise HTTPException(
            status_code=404,
            detail=f"Blood type '{blood_type}' not found. Valid types: {BLOOD_TYPES}",
        )

    models = _metrics_cache.get("models", {})
    if blood_type not in models:
        raise HTTPException(
            status_code=404,
            detail=f"No metrics available for blood type '{blood_type}'.",
        )

    m = models[blood_type]
    return {
        "model_version":     _metrics_cache.get("model_version"),
        "last_evaluated":    _metrics_cache.get("last_evaluated"),
        "evaluation_method": _metrics_cache.get("evaluation_method"),
        "blood_type":        blood_type,
        "mae":               m.get("mae"),
        "rmse":              m.get("rmse"),
        "mape":              m.get("mape"),
        "r2_score":          m.get("r2_score"),
        "evaluation_status": m.get("status"),
        "sample_size":       m.get("sample_size"),
        "test_period":       m.get("test_period"),
        "grading_scale":     _metrics_cache.get("grading_scale"),
    }


@app.post(
    "/model/metrics/refresh",
    summary="Recompute and refresh model metrics",
    tags=["Model Metrics"],
    response_description="Freshly computed metrics for all blood-type models.",
)
def refresh_metrics():
    """
    Force a full recomputation of all model evaluation metrics and update
    the on-disk cache.  Call this after uploading a new dataset or
    retraining models.
    """
    global _metrics_cache
    _metrics_cache = build_metrics_report(_demand_df)
    save_metrics(_metrics_cache)
    return {"status": "refreshed", "metrics": _metrics_cache}