# Blood Demand Forecasting Module - Quick Reference Guide

## 🚀 Getting Started

### Start the API Server
```bash
cd /workspaces/BloodLink_AI_Service
python -m uvicorn api.main:app --reload --port 8000
```

### Access the Dashboard
Open in browser: `http://localhost:8000/dashboard.html`

### View API Documentation
Open in browser: `http://localhost:8000/docs` (Swagger UI)

---

## 📊 API Endpoints Quick Reference

### 1. Monthly Forecast

```bash
# Get all predictions for next 12 months
curl "http://localhost:8000/forecast/monthly"

# Filter by O+ blood type
curl "http://localhost:8000/forecast/monthly?blood_type=O%2B"

# Filter by component type
curl "http://localhost:8000/forecast/monthly?component_type=Whole%20Blood"

# Combined filters for 6 months
curl "http://localhost:8000/forecast/monthly?blood_type=A%2B&component_type=Packed%20Red%20Cells&months_ahead=6"

# All negative blood types for 18 months
curl "http://localhost:8000/forecast/monthly?blood_type=O-&months_ahead=18"
```

### 2. Yearly Forecast

```bash
# Get predictions for next 3 years
curl "http://localhost:8000/forecast/yearly"

# Filter by A- blood type for 5 years
curl "http://localhost:8000/forecast/yearly?blood_type=A-&years_ahead=5"

# Filter by Fresh Frozen Plasma for 3 years
curl "http://localhost:8000/forecast/yearly?component_type=Fresh%20Frozen%20Plasma"

# Combined filters
curl "http://localhost:8000/forecast/yearly?blood_type=AB%2B&component_type=Cryoprecipitate&years_ahead=3"
```

### 3. Metadata Endpoints

```bash
# Get all blood types
curl "http://localhost:8000/forecast/blood-types"

# Get all component types
curl "http://localhost:8000/forecast/component-types"

# Get forecast capabilities
curl "http://localhost:8000/forecast/info"
```

---

## 🩸 Blood Types & Components

### Blood Types (8)
- O+, O-, A+, A-, B+, B-, AB+, AB-

### Component Types (5)
- Whole Blood
- Packed Red Cells
- Fresh Frozen Plasma
- Platelets Concentrate
- Cryoprecipitate

---

## 🐍 Python Usage Examples

### Monthly Forecast
```python
from model.forecast_generator import MonthlyForecastGenerator

# Initialize generator
gen = MonthlyForecastGenerator()

# Get all monthly forecasts
all_forecasts = gen.get_monthly_forecast()

# Filter by blood type
o_plus = gen.get_monthly_forecast(blood_type='O+')

# Filter by component type
packed_cells = gen.get_monthly_forecast(
    component_type='Packed Red Cells'
)

# Combined filter for 6 months
specific = gen.get_monthly_forecast(
    blood_type='A+',
    component_type='Fresh Frozen Plasma',
    months_ahead=6
)

# Get as DataFrame (for analysis/visualization)
df = gen.get_monthly_forecast_table(months_ahead=12)
print(df.head())
```

### Yearly Forecast
```python
from model.forecast_generator import YearlyForecastGenerator

# Initialize generator
gen = YearlyForecastGenerator(growth_rate=0.08)

# Get all yearly forecasts
all_forecasts = gen.get_yearly_forecast()

# Filter by blood type
a_neg = gen.get_yearly_forecast(blood_type='A-', years_ahead=5)

# Filter by component
cryo = gen.get_yearly_forecast(
    component_type='Cryoprecipitate',
    years_ahead=3
)

# Get historical data + forecast for trending
historical, forecast = gen.get_historical_and_forecast(
    blood_type='O+',
    component_type='Whole Blood',
    years_ahead=3
)
```

---

## 📈 Dashboard Usage

### Step 1: Select Filters
- Choose blood type from dropdown (or leave blank for all)
- Choose component type from dropdown (or leave blank for all)

### Step 2: Set Forecast Period
- For monthly: Set months (1-24, default 12)
- For yearly: Set years (1-10, default 3)

### Step 3: Load Data
- Click "Load Monthly Forecast" or "Load Yearly Forecast"

### Step 4: View Results
- Charts display graphically
- Tables show detailed values
- Filter multiple combinations to compare

---

## 🔍 Response Format Examples

### Monthly Forecast Response
```json
{
  "status": "success",
  "forecast_type": "monthly",
  "filters": {
    "blood_type": "O+",
    "component_type": "Whole Blood"
  },
  "months_ahead": 12,
  "data": [
    {
      "blood_type": "O+",
      "component_type": "Whole Blood",
      "month": 4,
      "month_name": "April",
      "year": 2023,
      "predicted_units": 199
    }
  ]
}
```

### Yearly Forecast Response
```json
{
  "status": "success",
  "forecast_type": "yearly",
  "filters": {
    "blood_type": "A+",
    "component_type": "Packed Red Cells"
  },
  "years_ahead": 3,
  "growth_rate": 0.08,
  "data": [
    {
      "blood_type": "A+",
      "component_type": "Packed Red Cells",
      "year": 2024,
      "predicted_units": 709,
      "growth_rate": 0.08
    }
  ]
}
```

---

## ⚙️ Configuration

### Adjust Growth Rate (Yearly Forecast)
```python
from model.forecast_generator import YearlyForecastGenerator

# Use 10% growth rate instead of default 8%
gen = YearlyForecastGenerator(growth_rate=0.10)
forecasts = gen.get_yearly_forecast()
```

### Use Custom Data File
```python
from model.forecast_generator import MonthlyForecastGenerator

# Load data from custom path
gen = MonthlyForecastGenerator(
    data_path='path/to/your/data.csv'
)
```

---

## 🐛 Troubleshooting

### Issue: API returns "Not Found" for endpoint
**Solution:** Ensure you're using the new endpoints (`/forecast/monthly`, `/forecast/yearly`). The old `/forecast/daily` and `/forecast/weekly` endpoints have been removed.

### Issue: No data returned
**Solution:** 
1. Check if blood type spelling is correct (case-sensitive)
2. Verify component type spelling
3. Ensure simulation data file exists at `data/simulation_data_with_components.csv`
4. Try without filters to get all combinations

### Issue: JSON serialization error
**Solution:** Update to the latest version of the code. Version 2.0 properly converts all numpy types to Python native types.

### Issue: Dashboard not loading
**Solution:**
1. Ensure API server is running
2. Check browser console for CORS errors
3. Verify API is accessible at `http://localhost:8000`
4. Check that CORS is enabled in `api/main.py`

---

## 📊 Forecasting Algorithms

### Monthly Forecasting
1. **Group** historical data by blood_type, component_type, month
2. **Average** demand for each combination
3. **Project** with formula: `avg_demand × (1 + 0.08)^(months/12)`
4. **Return** monthly predictions

### Yearly Forecasting
1. **Aggregate** monthly data into yearly totals
2. **Identify** baseline (last known year)
3. **Project** with formula: `previous_year × (1 + growth_rate)`
4. **Return** yearly predictions with growth rate

---

## 📁 File Structure

```
/workspaces/BloodLink_AI_Service/
├── api/
│   └── main.py                              # FastAPI app with new endpoints
├── model/
│   ├── forecast_generator.py                # NEW: Main forecasting logic
│   ├── predictor.py                         # Deprecated
│   ├── data_loader.py                       # Can be deprecated
│   ├── holiday_data.py                      # Deprecated
│   └── stock_data.py                        # Deprecated
├── data/
│   ├── simulation_data_with_components.csv  # NEW: Component-based data
│   ├── blood_demand_data.csv                # Legacy
│   └── download.csv                         # Legacy
├── dashboard.html                           # NEW: Interactive UI
├── FORECASTING_MODULE_V2.md                 # NEW: Full documentation
├── IMPLEMENTATION_SUMMARY.md                # NEW: Implementation details
└── QUICK_REFERENCE.md                       # This file
```

---

## 📚 Additional Resources

- **Full Documentation:** See `FORECASTING_MODULE_V2.md`
- **Implementation Details:** See `IMPLEMENTATION_SUMMARY.md`
- **API Swagger UI:** `http://localhost:8000/docs`
- **Source Code:** `model/forecast_generator.py`
- **Dashboard:** `dashboard.html`

---

## ✅ Quick Health Check

```bash
# Test API is running
curl "http://localhost:8000/"

# Test monthly endpoint
curl "http://localhost:8000/forecast/monthly?months_ahead=1"

# Test yearly endpoint
curl "http://localhost:8000/forecast/yearly?years_ahead=1"

# All should return 200 OK with JSON data
```

---

## 🚀 Common Use Cases

### Scenario 1: Plan O+ Whole Blood Inventory
```bash
curl "http://localhost:8000/forecast/monthly?blood_type=O%2B&component_type=Whole%20Blood&months_ahead=6"
```

### Scenario 2: Analyze Negative Blood Type Demand
```bash
curl "http://localhost:8000/forecast/yearly?blood_type=O-&years_ahead=3"
```

### Scenario 3: Compare All Components for Single Type
```bash
curl "http://localhost:8000/forecast/monthly?blood_type=A%2B&months_ahead=12"
```

### Scenario 4: Project Rare Components (AB Types)
```bash
curl "http://localhost:8000/forecast/yearly?blood_type=AB%2B&component_type=Fresh%20Frozen%20Plasma&years_ahead=3"
```

---

## 📝 Notes

- All timestamps are in YYYY-MM-DD format
- Growth rate is 8% annually by default (configurable)
- All predictions are integers (units)
- Dataset should ideally have 1-2 years of historical data
- API response includes status field for error checking

---

**Version:** 2.0  
**Last Updated:** May 21, 2026  
**Status:** ✅ Production Ready  

