# src/load_data.py
import pandas as pd
import os

# Folder where CSVs are saved
HISTORICAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "historical_data")

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

    # Fallback directory: if path is not found in src/historical_data, try data/historical_data
    if not os.path.exists(file_path):
        alt_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "historical_data"))
        alt_file_path = os.path.join(alt_dir, file_name)
        if os.path.exists(alt_file_path):
            file_path = alt_file_path
            print(f"INFO: found historical file in alternative path: {file_path}")
        else:
            # Another fallback for local relative installs
            alt_dir2 = os.path.abspath(os.path.join(os.path.dirname(__file__), "historical_data"))
            alt_file_path2 = os.path.join(alt_dir2, file_name)
            if os.path.exists(alt_file_path2):
                file_path = alt_file_path2
                print(f"INFO: found historical file in alternative path: {file_path}")
            else:
                raise FileNotFoundError(f"CSV file not found: {file_path}. Run fetch_historical.py first.")
    
    # Load CSV
    df = pd.read_csv(file_path, skiprows=3, names=["Date", "Open", "High", "Low", "Close", "Volume"], parse_dates=["Date"])
    
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