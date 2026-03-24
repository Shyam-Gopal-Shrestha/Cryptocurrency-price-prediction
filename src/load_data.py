# src/load_data.py
import pandas as pd
import os

# Folder where CSVs are saved
HISTORICAL_DATA_DIR = "src/historical_data"

def load_crypto_data(symbol):
    """
    Loads historical CSV for a given crypto symbol.
    
    Args:
        symbol (str): Crypto symbol like 'BTC-USD', 'ETH-USD'
    
    Returns:
        df (pd.DataFrame): Full OHLCV dataframe
        X (pd.DataFrame): Features for ML (Open, High, Low, Volume)
        y (pd.Series): Target for ML (Close)
    """
    # Build file path
    file_name = f"{symbol}_historical.csv"
    file_path = os.path.join(HISTORICAL_DATA_DIR, file_name)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CSV file not found: {file_path}. Run fetch_historical.py first.")
    
    # Load CSV
    df = pd.read_csv(file_path, index_col=0, parse_dates=True)
    
    # Check for missing values and drop if any
    if df.isnull().values.any():
        print(f"Warning: Missing values found in {symbol}, dropping missing rows.")
        df = df.dropna()
    
    # Display first and last few rows
    print(f"\n=== {symbol} Dataset ===")
    print("First 5 rows:")
    print(df.head())
    print("\nLast 5 rows:")
    print(df.tail())
    print("\nSummary statistics:")
    print(df.describe())
    
    # Prepare features and target
    X = df[['Open', 'High', 'Low', 'Volume']]
    y = df['Close']
    
    return df, X, y

# Optional: Load all cryptos in folder
def load_all_cryptos():
    csv_files = [f for f in os.listdir(HISTORICAL_DATA_DIR) if f.endswith(".csv")]
    crypto_data = {}
    
    for file in csv_files:
        symbol = file.replace("_historical.csv", "")
        df, X, y = load_crypto_data(symbol)
        crypto_data[symbol] = {"df": df, "X": X, "y": y}
    
    return crypto_data

# Example usage
if __name__ == "__main__":
    # Load single crypto
    df, X, y = load_crypto_data("BTC-USD")
    
    # Or load all cryptos
    # all_data = load_all_cryptos()