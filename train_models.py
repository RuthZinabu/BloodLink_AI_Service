import os
import pickle
from prophet import Prophet
from model.data_loader import load_historical_demand, BLOOD_TYPES
from model.holiday_data import get_ethiopian_holidays


MODEL_DIR = os.path.join(os.path.dirname(__file__), "model_files")


def train_models(data_file: str = None):
    df = load_historical_demand(data_file)
    holidays = get_ethiopian_holidays()

    os.makedirs(MODEL_DIR, exist_ok=True)

    for bt in BLOOD_TYPES:
        df_prophet = df[["date", bt]].rename(columns={"date": "ds", bt: "y"})

        model = Prophet(
            holidays=holidays,
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
        )

        model.fit(df_prophet)

        model_path = os.path.join(MODEL_DIR, f"prophet_{bt}_model.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(model, f)

        print(f"Saved model for {bt}: {model_path}")

    print("Training complete. Models saved to model_files/")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Train blood demand Prophet models using real historical demand data."
    )
    parser.add_argument(
        "--data-file",
        default=None,
        help="Optional path to a real blood demand CSV file. Defaults to data/download.csv or data/blood_demand_data.csv.",
    )
    args = parser.parse_args()

    train_models(args.data_file)
