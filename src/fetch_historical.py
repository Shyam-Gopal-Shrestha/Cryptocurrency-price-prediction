import yfinance as yf
import pandas as pd
import os

# List of cryptos you want
cryptos = ["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD"]

# Folder to save CSV files
output_dir = "src/historical_data"
os.makedirs(output_dir, exist_ok=True)

for crypto in cryptos:
    print(f"Fetching historical data for {crypto}...")
    data = yf.download(crypto, start="2015-01-01", end=None)  # up to today

    # Optional: keep only OHLCV
    data = data[['Open', 'High', 'Low', 'Close', 'Volume']]

    # Save to CSV
    file_path = os.path.join(output_dir, f"{crypto}_historical.csv")
    data.to_csv(file_path)
    print(f"Saved {crypto} data to {file_path}")