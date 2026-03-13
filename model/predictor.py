import pandas as pd
import pickle
import os
from model.holiday_data import get_ethiopian_holidays
from model.stock_data import get_current_stock

# -------------------------
# Load all trained models
# -------------------------
MODEL_DIR = os.path.join(os.path.dirname(__file__), "../model_files")
blood_types = ["O+","A+","B+","AB+","O-","A-","B-","AB-"]

models = {}
for bt in blood_types:
    filename = f"prophet_{bt}_model.pkl"
    path = os.path.join(MODEL_DIR, filename)
    with open(path, "rb") as f:
        models[bt] = pickle.load(f)

# -------------------------
# Forecast function
# -------------------------
def forecast(days=30):
    ethiopian_holidays = get_ethiopian_holidays()
    current_stock = get_current_stock()

    future_dates = pd.date_range(start=pd.Timestamp.today().normalize(), periods=days)
    future_df = pd.DataFrame({"ds": future_dates})

    holiday_dates = ethiopian_holidays['ds'].dt.strftime('%Y-%m-%d').tolist()
    holiday_names = dict(zip(
        ethiopian_holidays['ds'].dt.strftime('%Y-%m-%d'),
        ethiopian_holidays['holiday']
    ))

    # Predict once per model
    all_forecasts = {}
    for bt, model in models.items():
        forecast = model.predict(future_df)
        all_forecasts[bt] = forecast['yhat'].round().astype(int).tolist()

    # Build output
    output = []
    for i, date in enumerate(future_dates):
        date_str = date.strftime("%Y-%m-%d")
        record = {"date": date_str}

        # Holiday check
        record["holiday"] = holiday_names.get(date_str)

        # Blood type predictions + shortage alerts
        shortage_alerts = []
        for bt in blood_types:
            predicted = all_forecasts[bt][i]
            record[bt] = predicted

            stock = current_stock.get(bt, 0)
            if predicted > stock:
                shortage_alerts.append(f"{bt} shortage: predicted {predicted}, stock {stock}")

        record["alerts"] = shortage_alerts if shortage_alerts else None
        output.append(record)

    return output