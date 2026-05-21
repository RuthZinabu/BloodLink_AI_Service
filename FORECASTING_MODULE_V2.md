# Blood Demand Forecasting Module - Version 2.0

## Overview

The Blood Demand Forecasting Module has been completely refactored to provide **Monthly** and **Yearly** forecasting capabilities. All daily and weekly forecasting features have been removed.

### Key Features

✅ **Monthly Forecasting** - Predict blood demand by month, grouped by blood type and component type  
✅ **Yearly Forecasting** - Project demand trends using 8% annual growth rate  
✅ **Flexible Filtering** - Filter by blood type (O+, O-, A+, A-, B+, B-, AB+, AB-) and component type  
✅ **Trend-Based Projection** - Uses historical data aggregation and growth rate modeling  
✅ **Component-Based Tracking** - Supports 5 blood component types  
✅ **Interactive Dashboard** - Real-time visualization with Chart.js  
✅ **RESTful API** - Clean JSON endpoints with query parameters  

---

## Blood Types & Component Types

### Blood Types (8)
- O+ (O Positive)
- O- (O Negative)
- A+ (A Positive)
- A- (A Negative)
- B+ (B Positive)
- B- (B Negative)
- AB+ (AB Positive)
- AB- (AB Negative)

### Component Types (5)
- Whole Blood
- Packed Red Cells
- Fresh Frozen Plasma
- Platelets Concentrate
- Cryoprecipitate

---

## Data Structure

### Simulation Dataset Format

The system uses a simulation dataset with the following structure:

```csv
date,blood_type,component_type,demand_units
2023-01-01,O+,Whole Blood,10
2023-01-01,O+,Packed Red Cells,12
2023-01-01,O+,Fresh Frozen Plasma,5
...
```

**File Location:** `data/simulation_data_with_components.csv`

---

## API Endpoints

### Base URL
```
http://localhost:8000
```

### 1. Monthly Forecast Endpoint

**Endpoint:** `GET /forecast/monthly`

**Description:** Returns monthly blood demand forecast grouped by blood type and component type.

**Query Parameters:**
- `blood_type` (optional): Filter by specific blood type (e.g., `O+`, `A-`, `B+`)
- `component_type` (optional): Filter by component type (e.g., `Whole Blood`, `Packed Red Cells`)
- `months_ahead` (optional): Number of months to forecast (1-24, default: 12)

**Example Requests:**

```bash
# Get all blood types and components for next 12 months
curl "http://localhost:8000/forecast/monthly"

# Filter by O+ blood type
curl "http://localhost:8000/forecast/monthly?blood_type=O%2B"

# Filter by O+ and Packed Red Cells for 6 months
curl "http://localhost:8000/forecast/monthly?blood_type=O%2B&component_type=Packed%20Red%20Cells&months_ahead=6"

# All A- combinations for 18 months
curl "http://localhost:8000/forecast/monthly?blood_type=A-&months_ahead=18"
```

**Response Format:**

```json
{
  "status": "success",
  "forecast_type": "monthly",
  "filters": {
    "blood_type": "O+",
    "component_type": "Packed Red Cells"
  },
  "months_ahead": 12,
  "data": [
    {
      "blood_type": "O+",
      "component_type": "Packed Red Cells",
      "month": 6,
      "month_name": "June",
      "year": 2026,
      "predicted_units": 120
    },
    {
      "blood_type": "O+",
      "component_type": "Packed Red Cells",
      "month": 7,
      "month_name": "July",
      "year": 2026,
      "predicted_units": 125
    }
  ]
}
```

---

### 2. Yearly Forecast Endpoint

**Endpoint:** `GET /forecast/yearly`

**Description:** Returns yearly blood demand forecast using trend-based projection. Uses 8% annual growth rate by default.

**Query Parameters:**
- `blood_type` (optional): Filter by specific blood type (e.g., `O+`, `A-`, `B+`)
- `component_type` (optional): Filter by component type
- `years_ahead` (optional): Number of years to forecast (1-10, default: 3)

**Example Requests:**

```bash
# Get all predictions for next 3 years
curl "http://localhost:8000/forecast/yearly"

# Filter by A- blood type for 5 years
curl "http://localhost:8000/forecast/yearly?blood_type=A-&years_ahead=5"

# Filter by AB+ and Fresh Frozen Plasma
curl "http://localhost:8000/forecast/yearly?blood_type=AB%2B&component_type=Fresh%20Frozen%20Plasma&years_ahead=3"
```

**Response Format:**

```json
{
  "status": "success",
  "forecast_type": "yearly",
  "filters": {
    "blood_type": "O+",
    "component_type": "Whole Blood"
  },
  "years_ahead": 3,
  "growth_rate": 0.08,
  "data": [
    {
      "blood_type": "O+",
      "component_type": "Whole Blood",
      "year": 2027,
      "predicted_units": 3456,
      "growth_rate": 0.08
    },
    {
      "blood_type": "O+",
      "component_type": "Whole Blood",
      "year": 2028,
      "predicted_units": 3732,
      "growth_rate": 0.08
    }
  ]
}
```

---

### 3. Metadata Endpoints

#### Get Blood Types
**Endpoint:** `GET /forecast/blood-types`

```json
{
  "blood_types": ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
}
```

#### Get Component Types
**Endpoint:** `GET /forecast/component-types`

```json
{
  "component_types": [
    "Whole Blood",
    "Packed Red Cells",
    "Fresh Frozen Plasma",
    "Platelets Concentrate",
    "Cryoprecipitate"
  ]
}
```

#### Get Forecast Info
**Endpoint:** `GET /forecast/info`

Returns detailed information about forecasting capabilities, parameters, and growth rates.

---

## Backend Implementation

### Key Modules

#### 1. `model/forecast_generator.py`

Main module containing forecast generation logic.

**Classes:**

##### SimulationDataLoader
Handles loading and validating simulation data.

```python
from model.forecast_generator import SimulationDataLoader

df = SimulationDataLoader.load_simulation_data(
    data_path='data/simulation_data_with_components.csv'
)
```

##### MonthlyForecastGenerator
Generates monthly forecasts with optional filtering.

```python
from model.forecast_generator import MonthlyForecastGenerator

generator = MonthlyForecastGenerator()

# Get all monthly forecasts
all_forecasts = generator.get_monthly_forecast()

# Filter by blood type
o_plus_forecasts = generator.get_monthly_forecast(blood_type='O+')

# Filter by component type
packed_cells_forecasts = generator.get_monthly_forecast(
    component_type='Packed Red Cells'
)

# Combined filter for 6 months
specific = generator.get_monthly_forecast(
    blood_type='A+',
    component_type='Fresh Frozen Plasma',
    months_ahead=6
)

# Get as DataFrame (convenient for analysis)
df = generator.get_monthly_forecast_table(months_ahead=12)
```

##### YearlyForecastGenerator
Generates yearly forecasts with trend-based projection.

```python
from model.forecast_generator import YearlyForecastGenerator

generator = YearlyForecastGenerator(growth_rate=0.08)

# Get all yearly forecasts
all_forecasts = generator.get_yearly_forecast()

# With filters
a_neg_forecasts = generator.get_yearly_forecast(
    blood_type='A-',
    years_ahead=5
)

# Get as DataFrame
df = generator.get_yearly_forecast_table()

# Get historical data and forecast together (for trend visualization)
historical_df, forecast_df = generator.get_historical_and_forecast(
    blood_type='O+',
    component_type='Whole Blood',
    years_ahead=3
)
```

---

## Monthly Forecasting Algorithm

**Input:** Historical simulation data grouped by blood_type and component_type

**Process:**
1. Group data by year, month, blood_type, and component_type
2. Calculate average demand for each combination
3. Generate forecasts for `months_ahead` periods
4. Apply growth factor: `avg_demand × (1 + 0.08)^(months/12)`

**Output:** List of monthly predictions with structure:
```python
{
    'blood_type': str,
    'component_type': str,
    'month': int,
    'month_name': str,
    'year': int,
    'predicted_units': int
}
```

---

## Yearly Forecasting Algorithm

**Input:** Historical data aggregated into yearly totals

**Process:**
1. Aggregate monthly data into yearly totals per blood_type and component_type
2. Identify baseline year and demand
3. Generate projections for `years_ahead` periods
4. Apply growth formula: `previous_year × (1 + growth_rate)`
5. Default growth_rate: 8% annually

**Output:** List of yearly predictions with structure:
```python
{
    'blood_type': str,
    'component_type': str,
    'year': int,
    'predicted_units': int,
    'growth_rate': float
}
```

**Example Projection:**
```
2023 (Baseline): 1,000 units
2024: 1,000 × 1.08 = 1,080 units
2025: 1,080 × 1.08 = 1,166 units
2026: 1,166 × 1.08 = 1,259 units
2027: 1,259 × 1.08 = 1,360 units
```

---

## Dashboard Interface

### Features

- **Responsive Design:** Works on desktop, tablet, and mobile
- **Real-time Chart Updates:** Interactive visualizations using Chart.js
- **Dual Forecasting Views:** Side-by-side monthly and yearly panels
- **Flexible Filtering:** Drop-down filters for blood type and component
- **Data Tables:** Formatted tables showing detailed predictions
- **API Documentation:** Built-in reference for API endpoints

### Access Dashboard

```bash
# Open in browser
http://localhost:8000/dashboard.html
```

or open `dashboard.html` directly in a browser

### Usage

1. **Monthly Forecast Panel:**
   - Select blood type (or leave blank for all)
   - Select component type (or leave blank for all)
   - Set months to forecast (1-24)
   - Click "Load Monthly Forecast"
   - View line chart and data table

2. **Yearly Forecast Panel:**
   - Select blood type (or leave blank for all)
   - Select component type (or leave blank for all)
   - Set years to forecast (1-10)
   - Click "Load Yearly Forecast"
   - View trend line chart and data table

---

## Setup & Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Ensure you have:
- pandas
- fastapi
- uvicorn

### 2. Prepare Data

Ensure `data/simulation_data_with_components.csv` exists with the required columns:
- `date` - Date in YYYY-MM-DD format
- `blood_type` - One of the 8 blood types
- `component_type` - One of the 5 component types
- `demand_units` - Integer demand quantity

### 3. Start API Server

```bash
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Access Dashboard

- Open browser and navigate to: `http://localhost:8000/dashboard.html`
- Or use the Swagger UI: `http://localhost:8000/docs`

---

## Migration from Version 1.0

### Removed Features
- Daily forecasting (`/forecast/daily`)
- Weekly forecasting (`/forecast/weekly`)
- Holiday integration
- Stock-based shortage alerts
- Prophet model dependency

### What Changed
- API endpoints updated with new structure
- Data format changed to include component types
- Forecasting algorithm simplified to trend-based projection
- Dashboard completely redesigned

### Breaking Changes
Old endpoints no longer work:
- ❌ `/forecast/daily` → ✅ `/forecast/monthly`
- ❌ `/forecast/weekly` → ✅ `/forecast/monthly`
- ✅ `/forecast/monthly` (updated format)
- ✅ `/forecast/yearly` (same, but enhanced)

---

## Performance Optimization

### Query Optimization
- Data is grouped efficiently using pandas groupby
- Filtering happens at the grouping stage
- No unnecessary data processing

### Memory Usage
- Simulation data loaded once on startup
- Aggregations computed on-demand
- Large datasets handled with streaming

### Caching Recommendations
For production deployment:
1. Cache frequently requested combinations
2. Pre-compute popular filters
3. Implement Redis for session caching
4. Use CDN for dashboard assets

---

## Error Handling

### Invalid Blood Type
```json
{
  "status": "error",
  "message": "Invalid blood type: XYZ. Must be one of ['O+', 'O-', ...]"
}
```

### Invalid Component Type
```json
{
  "status": "error",
  "message": "Invalid component type: Invalid. Must be one of [...]"
}
```

### Missing Data File
```
FileNotFoundError: Simulation data not found at data/simulation_data_with_components.csv
```

---

## Example Use Cases

### Scenario 1: Plan Monthly O+ Whole Blood Inventory
```bash
curl "http://localhost:8000/forecast/monthly?blood_type=O%2B&component_type=Whole%20Blood&months_ahead=6"
```

### Scenario 2: Project Future Demand for All Blood Negatives
```bash
curl "http://localhost:8000/forecast/yearly?blood_type=O-&years_ahead=5"
```

### Scenario 3: Analyze Cryoprecipitate Trends Across All Types
```bash
curl "http://localhost:8000/forecast/yearly?component_type=Cryoprecipitate&years_ahead=3"
```

---

## Testing

Run the following to test the implementation:

```python
from model.forecast_generator import MonthlyForecastGenerator, YearlyForecastGenerator

# Test monthly
monthly = MonthlyForecastGenerator()
monthly_data = monthly.get_monthly_forecast(blood_type='O+', months_ahead=6)
print(f"Monthly predictions: {len(monthly_data)} records")

# Test yearly
yearly = YearlyForecastGenerator()
yearly_data = yearly.get_yearly_forecast(blood_type='A+', years_ahead=3)
print(f"Yearly predictions: {len(yearly_data)} records")
```

---

## Future Enhancements

- [ ] Machine learning models for better predictions
- [ ] Seasonal adjustment factors
- [ ] Holiday impact analysis
- [ ] Export to Excel/PDF
- [ ] User authentication
- [ ] Database backend for data persistence
- [ ] Mobile app integration
- [ ] Real-time alerts

---

## Support & Documentation

- **API Docs:** http://localhost:8000/docs
- **Source Code:** See `/model/forecast_generator.py`
- **Dashboard:** See `/dashboard.html`

