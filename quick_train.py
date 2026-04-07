#!/usr/bin/env python3
"""
Quick script to run model training and display results.
Usage: python quick_train.py
"""

import sys
sys.path.append('.')
from src.load_data import load_crypto_data
from src.models.linear_regression import train_linear_regression, evaluate_linear_regression
from src.models.random_forest import train_random_forest, evaluate_random_forest
from src.models.xgboost import train_xgboost, evaluate_xgboost
from src.models.svr import train_svr, evaluate_svr
from src.models.lstm import train_lstm, evaluate_lstm
import pandas as pd

def main():
    print("🔄 Loading data...")
    df, _, _ = load_crypto_data('BTC-USD')
    df = df.dropna()
    
    train_size = int(0.7 * len(df))
    X = df[['Open', 'High', 'Low', 'Volume']].values
    y = df['Close'].values
    X_train, X_test = X[:train_size], X[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]
    
    print(f"📊 Dataset: {len(df)} samples (Train: {len(X_train)}, Test: {len(X_test)})\n")
    
    models = {
        'Linear Regression': (train_linear_regression, evaluate_linear_regression),
        'Random Forest': (train_random_forest, evaluate_random_forest),
        'XGBoost': (train_xgboost, evaluate_xgboost),
        'SVR': (train_svr, evaluate_svr),
        'LSTM': (train_lstm, evaluate_lstm),
    }
    
    print("🤖 Training all models...\n")
    results = {}
    for name, (train_func, eval_func) in models.items():
        try:
            print(f"   {name}...", end=" ", flush=True)
            if name == 'LSTM':
                train_func(y_train, y_train, seq_length=30)
                results[name] = eval_func(y_test, y_test, seq_length=30)
            else:
                train_func(X_train, y_train)
                results[name] = eval_func(X_test, y_test)
            print("✓")
        except Exception as e:
            print(f"✗ ({str(e)[:50]}...)")
            results[name] = {'MAE': float('nan'), 'RMSE': float('nan'), 
                           'MAPE': float('nan'), 'R2': float('nan'), 
                           'Directional_Accuracy': float('nan')}
    
    print("\n" + "="*90)
    print("📈 MODEL COMPARISON RESULTS")
    print("="*90)
    results_df = pd.DataFrame(results).T
    print(results_df.to_string())
    print("="*90)
    
    # Find best model
    try:
        best = min(results, key=lambda m: results[m]['RMSE'])
        print(f"\n🏆 Best Model: {best} (RMSE: {results[best]['RMSE']:.2f})")
    except:
        print("\n⚠️ Could not determine best model (NaN values present)")
    
    print("\n✅ Training complete!")

if __name__ == "__main__":
    main()
