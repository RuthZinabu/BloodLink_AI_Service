from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from model.predictor import forecast as forecast_func
import pandas as pd

app = FastAPI(
    title="Blood Demand Forecast API",
    description="Forecast blood demand with holidays and stock alerts",
    version="1.0.0"
)

# Allow CORS (for your React frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "AI Forecast Service is running 🚀"}

# -----------------------------
# Forecast endpoints
# -----------------------------

@app.get("/forecast/daily")
def forecast_daily():
    """Return daily blood demand forecast for next 30 days"""
    return forecast_func(days=30)

@app.get("/forecast/weekly")
def forecast_weekly():
    """Return weekly forecast for next 12 weeks"""
    daily_data = forecast_func(days=84)  # 12 weeks
    # Aggregate per week
    df = pd.DataFrame(daily_data)
    df['week'] = pd.to_datetime(df['date']).dt.isocalendar().week
    weekly = df.groupby('week').agg({bt: 'sum' for bt in df.columns if bt in df.columns[:8]}).reset_index()
    return weekly.to_dict(orient='records')

@app.get("/forecast/monthly")
def forecast_monthly():
    """Return monthly forecast for next 12 months"""
    daily_data = forecast_func(days=365)  # 1 year
    df = pd.DataFrame(daily_data)
    df['month'] = pd.to_datetime(df['date']).dt.to_period('M')
    monthly = df.groupby('month').agg({bt: 'sum' for bt in df.columns if bt in df.columns[:8]}).reset_index()
    monthly['month'] = monthly['month'].astype(str)
    return monthly.to_dict(orient='records')

@app.get("/forecast/yearly")
def forecast_yearly():
    """Return yearly forecast for next 2 years"""
    daily_data = forecast_func(days=730)  # 2 years
    df = pd.DataFrame(daily_data)
    df['year'] = pd.to_datetime(df['date']).dt.year
    yearly = df.groupby('year').agg({bt: 'sum' for bt in df.columns if bt in df.columns[:8]}).reset_index()
    return yearly.to_dict(orient='records')

@app.get("/forecast/shortages")
def next_7day_shortages():
    """
    Returns critical blood shortages for the next 7 days.
    Only days with shortages are included.
    """
    daily_data = forecast_func(days=7)  # next 7 days
    shortages = []

    for day in daily_data:
        if day.get("alerts"):  # only include if there are shortages
            shortages.append({
                "date": day["date"],
                "holiday": day["holiday"],
                "alerts": day["alerts"]
            })

    return shortages