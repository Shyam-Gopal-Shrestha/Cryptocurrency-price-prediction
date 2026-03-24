# src/model.py
import os
import joblib
import pandas as pd
from sklearn.linear_model import LinearRegression

# Folder to save/load models
MODEL_DIR = "src/models"
os.makedirs(MODEL_DIR, exist_ok=True)

def train_model(df, model_name):
    """
    Train a Linear Regression model on a crypto DataFrame and save it.

    Args:
        df (pd.DataFrame): Historical OHLCV data
        model_name (str): Name of model to save (without .pkl)
    
    Returns:
        model: Trained LinearRegression model
    """
    # Convert to numeric and drop NaNs
    X = df[['Open', 'High', 'Low', 'Volume']].apply(pd.to_numeric, errors='coerce').dropna()
    y = pd.to_numeric(df['Close'], errors='coerce').loc[X.index]

    model = LinearRegression()
    model.fit(X, y)

    model_path = os.path.join(MODEL_DIR, f"{model_name}.pkl")
    joblib.dump(model, model_path)
    print(f"Saved model: {model_path}")
    return model

def load_model(model_name):
    """
    Load a trained model by name.

    Args:
        model_name (str): Name of model (without .pkl)
    
    Returns:
        model: Loaded LinearRegression model
    """
    model_path = os.path.join(MODEL_DIR, f"{model_name}.pkl")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    return joblib.load(model_path)

def predict_price(model_name, input_data):
    """
    Predict the Close price for a given crypto using a saved model.

    Args:
        model_name (str): Name of model (e.g., 'BTC_USD')
        input_data (dict or pd.DataFrame): Features dict or DataFrame with ['Open','High','Low','Volume']
    
    Returns:
        list: Predicted Close price(s)
    """
    model = load_model(model_name)

    # Convert dict to DataFrame if needed
    if isinstance(input_data, dict):
        input_df = pd.DataFrame([input_data])
    else:
        input_df = input_data

    # Ensure numeric
    input_df = input_df.apply(pd.to_numeric, errors='coerce')
    if input_df.isnull().values.any():
        raise ValueError("Input data contains non-numeric values")

    return model.predict(input_df).tolist()