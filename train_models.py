import sys
sys.path.append('.')
import pandas as pd
from src.load_data import load_crypto_data
from src.models.linear_regression import train_linear_regression, evaluate_linear_regression
from src.models.random_forest import train_random_forest, evaluate_random_forest
from src.models.xgboost import train_xgboost, evaluate_xgboost
from src.models.svr import train_svr, evaluate_svr
from src.models.lstm import train_lstm, evaluate_lstm

print("Loading and preprocessing data...")
# Load and preprocess data
df, _, _ = load_crypto_data('BTC-USD')
df = df.dropna()  # Basic clean

# Split
train_size = int(0.7 * len(df))
X = df[['Open', 'High', 'Low', 'Volume']].values  # Only basic features
y = df['Close'].values
X_train, X_test = X[:train_size], X[train_size:]
y_train, y_test = y[:train_size], y[train_size:]

print(f"Training set size: {X_train.shape[0]}, Test set size: {X_test.shape[0]}")

# Train and evaluate all models
models = {
    'Linear Regression': (train_linear_regression, evaluate_linear_regression),
    'Random Forest': (train_random_forest, evaluate_random_forest),
    'XGBoost': (train_xgboost, evaluate_xgboost),
    'SVR': (train_svr, evaluate_svr),
    'LSTM': (train_lstm, evaluate_lstm),
}

print("\nTraining models...")
results = {}
for name, (train_func, eval_func) in models.items():
    try:
        print(f"  Training {name}...", end=" ")
        if name == 'LSTM':
            train_func(y_train, y_train, seq_length=30)
            results[name] = eval_func(y_test, y_test, seq_length=30)
        else:
            train_func(X_train, y_train)
            results[name] = eval_func(X_test, y_test)
        print("✓")
    except Exception as e:
        print(f"✗ (Error: {e})")
        results[name] = {'MAE': float('nan'), 'RMSE': float('nan'), 'MAPE': float('nan'), 'R2': float('nan'), 'Directional_Accuracy': float('nan')}

# Display results
print("\n" + "="*100)
print("MODEL COMPARISON RESULTS")
print("="*100)
results_df = pd.DataFrame(results).T
print(results_df)
print("="*100)

# Select best model by RMSE
try:
    best_model = min(results, key=lambda x: results[x]['RMSE'])
    best_rmse = results[best_model]['RMSE']
    print(f"\n✓ Best model: {best_model} (RMSE: {best_rmse:.2f})")
except Exception as e:
    print(f"\nNote: Could not determine best model due to NaN values")

print("\nDone!")
