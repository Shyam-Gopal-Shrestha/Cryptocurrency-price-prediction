import yfinance as yf
import pandas as pd
from sklearn.linear_model import LinearRegression
import joblib
import os

MODEL_DIR = "src/models"
os.makedirs(MODEL_DIR, exist_ok=True)

cryptos = ["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD"]

for crypto in cryptos:
    print(f"\nTraining {crypto}...")

    # Download historical data
    data = yf.download(crypto, start="2015-01-01", end=None)
    if data.empty:
        print(f"No data for {crypto}")
        continue

    # Make a clean DataFrame
    df = pd.DataFrame(data)

    # Restrict to the required columns and confirm they exist
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        print(f"Missing columns for {crypto}: {missing_cols}, skipping...")
        continue

    df = df[required_cols].copy()

    # Convert remaining columns to numeric
    df = df.apply(lambda s: pd.to_numeric(s, errors='coerce'))

    # Drop rows with NaNs (safe because we only have required columns)
    df = df.dropna()
    
    # Prepare features and target
    X = df[['Open', 'High', 'Low', 'Volume']]
    y = df['Close']

    if len(X) == 0:
        print(f"No valid numeric data for {crypto}, skipping...")
        continue

    print(f"Number of rows used for {crypto}: {len(X)}")

    # Train model
    model = LinearRegression()
    model.fit(X, y)

    # Save model
    model_name = crypto.replace("-", "_") + ".pkl"
    model_path = os.path.join(MODEL_DIR, model_name)
    joblib.dump(model, model_path)
    print(f"{crypto} model saved to {model_path}")