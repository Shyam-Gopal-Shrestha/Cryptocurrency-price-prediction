import yfinance as yf
import pandas as pd

def load_crypto_data(symbol, start="2022-01-01", end="2024-01-01"):
    """
    Load historical data for any cryptocurrency
    """
    print(f"Loading data for {symbol}...")

    data = yf.download(symbol, start=start, end=end)

    if data.empty:
        print(f"No data found for {symbol}")
        return None

    df = pd.DataFrame(data)

    return df