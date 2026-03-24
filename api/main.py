# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.model import predict_price  # use the modular model
import os
import pandas as pd

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to your React URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Input schema for POST request
class InputData(BaseModel):
    symbol: str
    Open: float
    High: float
    Low: float
    Volume: float

@app.get("/")
def home():
    return {"message": "Crypto Price Prediction API Running"}

@app.post("/predict")
def predict(data: InputData):
    """
    Predict Close price for any crypto using pre-trained model.
    """
    try:
        # Convert symbol to model name, e.g., BTC-USD -> BTC_USD
        model_name = data.symbol.replace("-", "_")

        # Prepare input dictionary
        input_data = {
            "Open": data.Open,
            "High": data.High,
            "Low": data.Low,
            "Volume": data.Volume
        }

        # Get prediction using src.model
        prediction = predict_price(model_name, input_data)

        return {"symbol": data.symbol, "prediction": prediction}

    except FileNotFoundError as fe:
        return {"error": str(fe)}

    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

@app.get("/historical")
def get_historical(symbol: str, date: str):
    """Fetch Open/High/Low/Volume for a symbol on a given date from CSV."""

    # Historical files are named using dash punctuation (e.g. BTC-USD_historical.csv)
    csv_symbol = symbol
    file_path = os.path.join("src", "historical_data", f"{csv_symbol}_historical.csv")

    # Support older path style if users passed underscore form
    if not os.path.isfile(file_path):
        alt_symbol = symbol.replace("_", "-")
        alt_path = os.path.join("src", "historical_data", f"{alt_symbol}_historical.csv")
        if os.path.isfile(alt_path):
            file_path = alt_path
    if not os.path.isfile(file_path):
        return {"error": f"No historical data for symbol {symbol}."}

    try:
        # Historical CSV has three header rows (Price/Ticker/Date row) before data, so skip them.
        df = pd.read_csv(
            file_path,
            skiprows=3,
            names=["Date", "Open", "High", "Low", "Close", "Volume"],
            parse_dates=["Date"],
        )
    except Exception as e:
        return {"error": f"Failed to read historical data: {str(e)}"}

    try:
        selected_date = pd.to_datetime(date)
    except Exception as e:
        return {"error": f"Invalid date format: {str(e)}"}

    row = df.loc[df["Date"] == selected_date]
    if row.empty:
        # fallback: use the latest available date before requested date
        row = df.loc[df["Date"] <= selected_date].sort_values(by="Date", ascending=False)
        if row.empty:
            return {"error": f"Date {date} not found for {symbol}."}
        row = row.iloc[0]
        match_date = row["Date"].strftime("%Y-%m-%d")
    else:
        row = row.iloc[0]
        match_date = date

    return {
        "symbol": symbol,
        "date": match_date,
        "symbol": symbol,
        "date": date,
        "Open": float(row.get("Open", 0)),
        "High": float(row.get("High", 0)),
        "Low": float(row.get("Low", 0)),
        "Volume": float(row.get("Volume", 0)),
    }