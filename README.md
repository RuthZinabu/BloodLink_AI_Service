# 🩸 BloodLink AI Service v2.0 – Blood Demand Forecasting System

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Production-green)
![Forecasting](https://img.shields.io/badge/Forecasting-Blood%20Demand-red)
![Status](https://img.shields.io/badge/Status-Production%20Ready-success)

A production-ready forecasting system for blood demand prediction in hospitals and blood banks, providing monthly and yearly forecasts grouped by blood type and component type for data-driven inventory management.

---

# 📑 Table of Contents

- Overview
- What Changed in v2.0
- Features
- Quick Start
- API Examples
- Python Usage 
- Data Sources
- Model Training
- Annual Dataset Upload & Automatic Retraining
- Development

---

# 🩸 Overview

**BloodLink AI Service v2.0** is a production-ready forecasting system for blood demand prediction in hospitals and blood banks. The system provides **monthly and yearly forecasts** grouped by blood type and component type, enabling data-driven inventory management.

## ✨ What Changed in v2.0

- ✅ Simplified Architecture
- ✅ Component-Based Tracking
- ✅ Interactive Dashboard
- ✅ Clean API Design
- ✅ Production-Ready Codebase

---

# 🎯 Features

## Forecasting Capabilities

| Capability | Description |
|------------|-------------|
| Monthly Forecasting | Predict demand for each month grouped by blood type and component |
| Yearly Forecasting | Project future years using trend-based analysis |
| Flexible Filtering | Filter by blood type, component type, or combinations |
| Shortage Prediction | Compare demand against inventory levels |
| Accurate Projections | Based on simulation dataset aggregation and growth projection |

## Supported Blood Types

| O+ | O- | A+ | A- |
|----|----|----|----|
| B+ | B- | AB+ | AB- |

## Supported Components

| Components |
|------------|
| Whole Blood |
| Packed Red Cells |
| Fresh Frozen Plasma |
| Platelets Concentrate |
| Cryoprecipitate |

## API & Dashboard

- RESTful API built with FastAPI
- Swagger/OpenAPI documentation
- Interactive dashboard with Chart.js
- Real-time charts and filtering
- Metadata endpoints
- CORS enabled for frontend integration

# 🚀 Quick Start

## Step 1 — Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2 — Start API Server

```bash
python -m uvicorn api.main:app --reload --port 8000
```

## Step 3 — Access Dashboard

```text
http://localhost:8000/dashboard.html
```

## Step 4 — View API Documentation

```text
http://localhost:8000/docs
```

---

# 📡 API Examples

## Monthly Forecast

```bash
curl "http://localhost:8000/forecast/monthly"

curl "http://localhost:8000/forecast/monthly?blood_type=O%2B&component_type=Whole%20Blood&months_ahead=6"
```

## Yearly Forecast

```bash
curl "http://localhost:8000/forecast/yearly"

curl "http://localhost:8000/forecast/yearly?blood_type=A-&years_ahead=5"
```

## Shortage Prediction

```bash
curl "http://localhost:8000/forecast/shortages"

curl "http://localhost:8000/forecast/shortages?blood_type=O%2B&component_type=Whole%20Blood"
```

---

# 🐍 Python Usage

Start using the provided script:

```bash
./start.sh
```

Or use uvicorn directly:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

The API will be available at:

```text
http://localhost:8000
```

# 📡 API Endpoints

| Method | Endpoint | Description |
|----------|----------|-------------|
| GET | /forecast/monthly | Monthly aggregated forecast |
| GET | /forecast/yearly | Yearly aggregated forecast |
| GET | /forecast/shortages | Inventory shortage prediction |
| POST | /model/upload-dataset | Upload annual dataset |
| GET | /model/status | Training status |

# 🗄️ Data Sources

## Historical Data

- `data/download.csv`
- Fallback: `data/blood_demand_data.csv`

## Holiday Data

- Ethiopian public holidays (2023–2030)
- Integrated into Prophet models

## Stock Data

- Retrieved dynamically from inventory backend
- Uses admin credentials for authenticated stock access

---

# 🤖 Model Training

The forecasting models are trained using Facebook Prophet.

## Training Process

1. Load historical blood demand data
2. Add Ethiopian holidays as regressors
3. Train one model per blood type
4. Save serialized models

## Retraining

```bash
python train_models.py --data-file data/download.csv
```

If your file name differs:

```bash
python train_models.py --data-file path/to/file.csv
```

---

# 🔄 Annual Dataset Upload & Automatic Retraining

This release introduces an administrator workflow for annual dataset uploads and automated retraining.

## Key Features

- Upload endpoint: `POST /model/upload-dataset`
- Status endpoint: `GET /model/status`
- Automatic validation
- Historical dataset merge
- Background Prophet retraining
- Metadata version tracking

## Required CSV Columns

```text
date,O+,A+,B+,AB+,O-,A-,B-,AB-
```

## Example Upload

```bash
curl -X POST "http://localhost:8000/model/upload-dataset" \
-H "X-Admin-Token: admin-secret" \
-F "file=@/path/to/annual_2027.csv"
```

## Check Status

```bash
curl "http://localhost:8000/model/status"
```

> ⚠️ Important: Uploading a dataset triggers retraining in the background. Restart the FastAPI service to ensure newly trained models are loaded immediately.

# 🛠️ Development

## Project Structure

```text
BloodLink_AI_Service/
├── api/
│   └── main.py
├── data/
│   ├── download.csv
│   ├── blood_demand_data.csv
│   └── predicted_demand.csv
├── model/
│   ├── predictor.py
│   ├── holiday_data.py
│   └── stock_data.py
├── model_files/
├── notebooks/
│   ├── blood_demand_generation.ipynb
│   └── blood_forecast_model.ipynb
├── requirements.txt
├── start.sh
└── README.md
```

## 📌 Summary

BloodLink AI Service v2.0 provides monthly and yearly blood demand forecasting, shortage prediction, inventory awareness, automated model retraining, and an interactive dashboard in a production-ready FastAPI architecture.
