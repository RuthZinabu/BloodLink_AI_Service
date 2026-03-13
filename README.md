# BloodLink AI Service

## Overview

BloodLink AI Service is an intelligent forecasting system designed to predict blood demand for hospitals and blood banks. Leveraging machine learning with Facebook Prophet, this service provides accurate daily, weekly, monthly, and yearly forecasts for all major blood types (O+, A+, B+, AB+, O-, A-, B-, AB-). The system incorporates Ethiopian holidays and current stock levels to generate actionable shortage alerts, helping healthcare providers optimize blood inventory management and prevent critical shortages.

## Features

- **Multi-Timeframe Forecasting**: Generate predictions for daily (30 days), weekly (12 weeks), monthly (12 months), and yearly (2 years) horizons.
- **Blood Type Coverage**: Comprehensive forecasting for all 8 major blood types.
- **Holiday Integration**: Accounts for Ethiopian public holidays that may affect blood demand patterns.
- **Stock Alert System**: Real-time shortage alerts when predicted demand exceeds current stock levels.
- **RESTful API**: FastAPI-based backend providing easy integration with existing healthcare systems.
- **Machine Learning Powered**: Uses Facebook Prophet for robust time series forecasting with seasonal and trend analysis.

## Architecture

The project consists of the following components:

- **API Layer** (`api/`): FastAPI application serving forecast endpoints
- **Model Layer** (`model/`): Core forecasting logic, holiday data, and stock management
- **Data Layer** (`data/`): Historical blood demand data and prediction outputs
- **Model Files** (`model_files/`): Serialized trained Prophet models
- **Notebooks** (`notebooks/`): Jupyter notebooks for data generation and model training

## Installation

### Prerequisites

- Python 3.8+
- pip package manager

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/RuthZinabu/BloodLink_AI_Service.git
   cd BloodLink_AI_Service
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure model files are present in `model_files/` directory (see Model Training section below).

## Usage

### Running the API Server

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

- `GET /forecast/daily` - Daily forecast for next 30 days
- `GET /forecast/weekly` - Weekly aggregated forecast for next 12 weeks
- `GET /forecast/monthly` - Monthly aggregated forecast for next 12 months
- `GET /forecast/yearly` - Yearly aggregated forecast for next 2 years

### Alert Endpoints

- `GET /forecast/shortages` - Critical blood shortages for next 7 days

### Response Format

Forecast responses include:
- `date`: Forecast date
- `holiday`: Holiday name (if applicable)
- Blood type quantities: `O+`, `A+`, `B+`, `AB+`, `O-`, `A-`, `B-`, `AB-`
- `alerts`: List of shortage alerts (when predicted demand > current stock)

## Data Sources

### Historical Data
- `data/blood_demand_data.csv`: Historical daily blood demand data (synthetic data for demonstration)
- Generated using statistical distributions with weekend adjustments and emergency spikes

### Holiday Data
- Ethiopian public holidays from 2023-2030
- Integrated into Prophet models for improved forecast accuracy

### Stock Data
- Current blood stock levels (currently hardcoded in `model/stock_data.py`)
- Can be updated to connect to real inventory systems

## Model Training

The forecasting models are trained using Facebook Prophet with the following process:

1. **Data Preparation**: Load historical blood demand data
2. **Holiday Integration**: Add Ethiopian holidays as regressors
3. **Model Training**: Train separate Prophet models for each blood type
4. **Model Serialization**: Save trained models to `model_files/` directory

To retrain models with new data:

1. Update `data/blood_demand_data.csv` with new historical data
2. Run the training notebook:
   ```bash
   jupyter notebook notebooks/blood_forecast_model.ipynb
   ```

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
│   ├── blood_demand_data.csv    # Historical demand data
│   └── predicted_demand.csv     # Forecast outputs
├── model/
│   ├── predictor.py         # Core forecasting logic
│   ├── holiday_data.py      # Ethiopian holiday data
│   └── stock_data.py        # Current stock levels
├── model_files/             # Trained model files
├── notebooks/
│   ├── blood_demand_generation.ipynb  # Data generation
│   └── blood_forecast_model.ipynb     # Model training
├── requirements.txt         # Python dependencies
├── start.sh                 # Startup script
└── README.md               # This file
```