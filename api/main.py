# api/main.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.model import predict_price  # use the modular model
from src.load_data import load_crypto_data
from src.models.linear_regression import train_linear_regression, evaluate_linear_regression
from src.models.random_forest import train_random_forest, evaluate_random_forest
from src.models.xgboost import train_xgboost, evaluate_xgboost
from src.models.svr import train_svr, evaluate_svr
from src.models.lstm import train_lstm, evaluate_lstm
from api.auth import router as auth_router
import pandas as pd
import numpy as np
import threading

app = FastAPI()
app.include_router(auth_router)

# Allow CORS for frontend (explicit whitelisted origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Input schema for POST request
class InputData(BaseModel):
    symbol: str
    model: str  # e.g., 'linear_regression', 'random_forest', etc.
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
    Predict Close price for any crypto using selected model.
    """
    try:
        print(f"[PREDICT] request model={data.model}, symbol={data.symbol}, data={{Open:{data.Open},High:{data.High},Low:{data.Low},Volume:{data.Volume}}}")
        # Convert symbol to model name, e.g., BTC-USD -> BTC_USD
        model_name = data.symbol.replace("-", "_")

        # Prepare input dictionary
        input_data = {
            "Open": data.Open,
            "High": data.High,
            "Low": data.Low,
            "Volume": data.Volume
        }

        # Import the appropriate model function
        if data.model == 'linear_regression':
            from src.models.linear_regression import predict_linear_regression
            prediction = predict_linear_regression([list(input_data.values())])
        elif data.model == 'random_forest':
            from src.models.random_forest import predict_random_forest
            prediction = predict_random_forest([list(input_data.values())])
        elif data.model == 'xgboost':
            from src.models.xgboost import predict_xgboost
            prediction = predict_xgboost([list(input_data.values())])
        elif data.model == 'svr':
            from src.models.svr import predict_svr
            prediction = predict_svr([list(input_data.values())])
        elif data.model == 'lstm':
            # LSTM needs historical sequence data, not just OHLV features
            # Load last 30 days of Close prices from historical data
            from src.models.lstm import predict_lstm
            csv_symbol = data.symbol
            file_path = os.path.join("src", "historical_data", f"{csv_symbol}_historical.csv")
            
            if not os.path.isfile(file_path):
                alt_symbol = data.symbol.replace("_", "-")
                alt_path = os.path.join("src", "historical_data", f"{alt_symbol}_historical.csv")
                if os.path.isfile(alt_path):
                    file_path = alt_path
            
            if not os.path.isfile(file_path):
                return {"error": f"No historical data for LSTM: {data.symbol}"}
            
            # Load historical data and get last 30 Close prices
            try:
                df = pd.read_csv(
                    file_path,
                    skiprows=3,
                    names=["Date", "Open", "High", "Low", "Close", "Volume"],
                    parse_dates=["Date"],
                )
                close_prices = df['Close'].tail(30).values
                prediction = predict_lstm(close_prices)
            except Exception as e:
                return {"error": f"Failed to predict with LSTM: {str(e)}"}
        else:
            return {"error": "Invalid model selected"}

        # Normalize prediction to scalar float for JSON serialization
        if hasattr(prediction, '__iter__'):
            pred_val = prediction[0]
        else:
            pred_val = prediction

        if isinstance(pred_val, (np.floating, np.integer)):
            pred_val = pred_val.item()

        return {"symbol": data.symbol, "model": data.model, "prediction": float(pred_val)}

    except FileNotFoundError as fe:
        print(f"[PREDICT][ERROR] FileNotFoundError: {fe}")
        return {"error": str(fe)}

    except Exception as e:
        print(f"[PREDICT][ERROR] Unexpected: {e}")
        return {"error": f"Unexpected error: {str(e)}"}

@app.get("/historical")
def get_historical(symbol: str, date: str = None):
    """Fetch historical rows by symbol, or a specific row if date is provided."""

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

    # When no date is provided, return recent rows for dashboard table rendering.
    if not date:
        recent_df = df.sort_values(by="Date", ascending=False).head(20).copy()
        recent_df["Date"] = recent_df["Date"].dt.strftime("%Y-%m-%d")
        return recent_df.to_dict(orient="records")

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
        "Open": float(row.get("Open", 0)),
        "High": float(row.get("High", 0)),
        "Low": float(row.get("Low", 0)),
        "Close": float(row.get("Close", 0)),
        "Volume": float(row.get("Volume", 0)),
    }

# Store training status
training_status = {"is_running": False, "progress": "", "results": None}

@app.get("/train/status")
def get_training_status():
    """Get current training status."""
    return training_status

@app.post("/train/models")
def train_models_endpoint():
    """
    Train all models (Linear Regression, Random Forest, XGBoost, SVR, LSTM).
    Returns immediately; check /train/status for progress.
    """
    global training_status
    
    if training_status["is_running"]:
        return {"status": "training", "message": "Model training already in progress"}
    
    def run_training():
        global training_status
        try:
            training_status["is_running"] = True
            training_status["progress"] = "Loading data..."
            
            # Load and preprocess data
            df, _, _ = load_crypto_data('BTC-USD')
            df = df.dropna()
            
            train_size = int(0.7 * len(df))
            X = df[['Open', 'High', 'Low', 'Volume']].values
            y = df['Close'].values
            X_train, X_test = X[:train_size], X[train_size:]
            y_train, y_test = y[:train_size], y[train_size:]
            
            training_status["progress"] = f"Training data loaded ({len(df)} samples)"
            
            # Train all models
            models = {
                'Linear Regression': (train_linear_regression, evaluate_linear_regression),
                'Random Forest': (train_random_forest, evaluate_random_forest),
                'XGBoost': (train_xgboost, evaluate_xgboost),
                'SVR': (train_svr, evaluate_svr),
                'LSTM': (train_lstm, evaluate_lstm),
            }
            
            results = {}
            for name, (train_func, eval_func) in models.items():
                training_status["progress"] = f"Training {name}..."
                try:
                    if name == 'LSTM':
                        train_func(y_train, y_train, seq_length=30)
                        results[name] = eval_func(y_test, y_test, seq_length=30)
                    else:
                        train_func(X_train, y_train)
                        results[name] = eval_func(X_test, y_test)
                except Exception as e:
                    results[name] = {'error': str(e)}
            
            # Convert results to serializable format
            serializable_results = {}
            for model, metrics in results.items():
                if isinstance(metrics, dict):
                    serializable_results[model] = {k: float(v) if not isinstance(v, str) else v for k, v in metrics.items()}
                else:
                    serializable_results[model] = {"error": str(metrics)}
            
            training_status["results"] = serializable_results
            training_status["progress"] = "Training complete!"
            
        except Exception as e:
            training_status["progress"] = f"Error: {str(e)}"
            training_status["results"] = {"error": str(e)}
        finally:
            training_status["is_running"] = False
    
    # Run training in background thread
    thread = threading.Thread(target=run_training, daemon=True)
    thread.start()
    
    return {"status": "started", "message": "Model training started. Check /train/status for progress."}

@app.get("/models/comparison")
def get_model_comparison():
    """Get the latest model comparison results."""
    if training_status["results"] is None:
        return {"message": "No training results yet. Run /train/models first."}
    return training_status["results"]
