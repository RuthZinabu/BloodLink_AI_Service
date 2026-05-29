# BloodLink AI Service - Blood Demand Forecasting System

## 🩸 Overview

**BloodLink AI Service v2.0** is a production-ready forecasting system for blood demand prediction in hospitals and blood banks. The system provides **monthly and yearly forecasts** grouped by blood type and component type, enabling data-driven inventory management.

### What Changed in v2.0 ✨

- ✅ **Simplified Architecture:** Removed daily and weekly forecasting for focused, production-ready monthly/yearly forecasts
- ✅ **Component-Based Tracking:** Group predictions by blood type AND component type (5 components supported)
- ✅ **Trend-Based Projection:** Uses 8% annual growth rate for reliable yearly forecasts
- ✅ **Interactive Dashboard:** Beautiful, responsive UI with Chart.js visualization
- ✅ **Clean API:** Flexible filtering by blood_type and component_type
- ✅ **Production-Ready Code:** Optimized queries, proper error handling, zero hardcoding

## 🎯 Features

### Forecasting Capabilities
- **Monthly Forecasting**: Predict demand for each month, grouped by blood type (8 types) and component (5 types)
- **Yearly Forecasting**: Project future years using trend-based analysis with configurable growth rate
- **Flexible Filtering**: Filter by blood type, component type, or view all combinations
- **Inventory-Aware Shortage Prediction**: Compare next month demand to available stock via connected inventory backend
- **Accurate Projections**: Based on simulation dataset aggregation and growth projection

### Blood Types & Components Supported
**Blood Types (8):** O+, O-, A+, A-, B+, B-, AB+, AB-  
**Components (5):** Whole Blood, Packed Red Cells, Fresh Frozen Plasma, Platelets Concentrate, Cryoprecipitate

### API & Dashboard
- **RESTful API**: FastAPI-based with Swagger/OpenAPI documentation
- **Interactive Dashboard**: Real-time charts, data tables, and filters
- **Metadata Endpoints**: Get available blood types, components, and capabilities
- **CORS Enabled**: Ready for frontend integration

## 📊 Architecture

```
BloodLink_AI_Service/
├── api/main.py                              # FastAPI endpoints (monthly/yearly)
├── model/forecast_generator.py              # Forecasting logic
├── data/simulation_data_with_components.csv # Component-based simulation data
├── dashboard.html                           # Interactive UI
├── QUICK_REFERENCE.md                       # Quick start guide
├── FORECASTING_MODULE_V2.md                 # Full documentation
└── IMPLEMENTATION_SUMMARY.md                # Technical details
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start API Server
```bash
python -m uvicorn api.main:app --reload --port 8000
```

### 3. Access Dashboard
Open browser: `http://localhost:8000/dashboard.html`

### 4. View API Docs
Open browser: `http://localhost:8000/docs` (Swagger UI)

## 📡 API Examples

### Monthly Forecast
```bash
# Get all monthly predictions for next 12 months
curl "http://localhost:8000/forecast/monthly"

# Filter by O+ blood type, Whole Blood component, for 6 months
curl "http://localhost:8000/forecast/monthly?blood_type=O%2B&component_type=Whole%20Blood&months_ahead=6"

# Response
{
  "status": "success",
  "forecast_type": "monthly",
  "filters": {"blood_type": "O+", "component_type": "Whole Blood"},
  "months_ahead": 6,
  "data": [
    {
      "blood_type": "O+",
      "component_type": "Whole Blood",
      "month": 6,
      "month_name": "June",
      "year": 2026,
      "predicted_units": 120
    },
    ...
  ]
}
```

### Yearly Forecast
```bash
# Get yearly predictions for next 3 years
curl "http://localhost:8000/forecast/yearly"

# Filter by A- blood type, 5 years
curl "http://localhost:8000/forecast/yearly?blood_type=A-&years_ahead=5"

# Response
{
  "status": "success",
  "forecast_type": "yearly",
  "filters": {"blood_type": "A-", "component_type": null},
  "years_ahead": 5,
  "growth_rate": 0.08,
  "data": [
    {
      "blood_type": "A-",
      "component_type": "Whole Blood",
      "year": 2027,
      "predicted_units": 3456,
      "growth_rate": 0.08
    },
    ...
  ]
}
```

### Shortage Prediction

```bash
# Get next month shortage risk across all blood types
curl "http://localhost:8000/forecast/shortages"

# Filter by O+ and Whole Blood
curl "http://localhost:8000/forecast/shortages?blood_type=O%2B&component_type=Whole%20Blood"
```

## 🐍 Python Usage

### Monthly Forecast

Start the FastAPI server using the provided script:

```bash
./start.sh
```

Or directly with uvicorn:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

### API Documentation

Once running, visit `http://localhost:8000/docs` for interactive Swagger UI documentation.

## API Endpoints

### Forecast Endpoints

- `GET /forecast/monthly` - Monthly aggregated forecast through the end of 2027
- `GET /forecast/yearly` - Yearly aggregated forecast through the end of 2027

### Alert Endpoints

- `GET /forecast/shortages` - Shortage prediction for the next calendar month based on current inventory

### Response Format

Forecast endpoints return JSON with:
- `status`: `success` or `error`
- `forecast_type`: `monthly` or `yearly`
- `filters`: selected blood type and component filters
- `months_ahead` / `years_ahead`: requested forecast horizon
- `data`: list of forecast records

Shortage endpoint returns:
- `forecast_month`, `forecast_year`
- `current_stock`: available inventory by blood type
- `shortages`: shortage records when demand exceeds stock
- `inventory_source`: backend inventory API URL

## Data Sources

### Historical Data
- `data/download.csv`: Historical blood demand data from the blood bank for real training
- If `data/download.csv` is unavailable, the system will also look for `data/blood_demand_data.csv`

### Holiday Data
- Ethiopian public holidays from 2023-2030
- Integrated into Prophet models for improved forecast accuracy

### Stock Data
- Current blood stock is now retrieved dynamically from an inventory backend via the `/api/inventory` API
- Admin credentials are used for authentication and shortage calculations

## Model Training

The forecasting models are trained using Facebook Prophet with the following process:

1. **Data Preparation**: Load historical blood demand data
2. **Holiday Integration**: Add Ethiopian holidays as regressors
3. **Model Training**: Train separate Prophet models for each blood type
4. **Model Serialization**: Save trained models to `model_files/` directory

To retrain models with new real-world data:

1. Place your historical blood bank demand data in `data/download.csv`
2. Run the training script:
   ```bash
   python train_models.py --data-file data/download.csv
   ```

If your file is named differently, pass its path using `--data-file`.

## Configuration

### Environment Variables

- `PORT`: Server port (default: 8000)

### Model Configuration

Models are configured in `notebooks/blood_forecast_model.ipynb`:
- Yearly seasonality: Enabled
- Weekly seasonality: Enabled
- Daily seasonality: Disabled
- Holiday effects: Ethiopian holidays with ±1 day window

## Development

### Project Structure

```
BloodLink_AI_Service/
├── api/
│   └── main.py              # FastAPI application
├── data/
│   ├── download.csv             # Real historical demand data from the blood bank
│   ├── blood_demand_data.csv    # Optional fallback demand data
│   └── predicted_demand.csv     # Forecast outputs
├── model/
│   ├── predictor.py         # Core forecasting logic
│   ├── holiday_data.py      # Ethiopian holiday data
│   └── stock_data.py        # Current stock levels
├── model_files/             # Trained model files
├── notebooks/
│   ├── blood_demand_generation.ipynb  # Legacy synthetic data generator (do not use for real data)
│   └── blood_forecast_model.ipynb     # Model training (use real data in data/download.csv)
├── requirements.txt         # Python dependencies
├── start.sh                 # Startup script
└── README.md               # This file
```