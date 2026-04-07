import sys
sys.path.append('..')
import pandas as pd
from src.load_data import load_crypto_data
from src.feature_engineering import preprocess_data
from src.models.linear_regression import train_linear_regression, evaluate_linear_regression
from src.models.random_forest import train_random_forest, evaluate_random_forest
from src.models.xgboost import train_xgboost, evaluate_xgboost
from src.models.svr import train_svr, evaluate_svr
# from src.models.lstm import train_lstm, evaluate_lstm

# Load and preprocess data
df, _, _ = load_crypto_data('BTC-USD')  # Example for one crypto
df = preprocess_data(df)

# Split data (simple for now; use time-aware from EDA)
train_size = int(0.7 * len(df))
X = df.drop(['Close', 'Date'], axis=1).values
y = df['Close'].values
X_train, X_test = X[:train_size], X[train_size:]
y_train, y_test = y[:train_size], y[train_size:]

# Train and evaluate models
models = {
    'Linear Regression': (train_linear_regression, evaluate_linear_regression),
    'Random Forest': (train_random_forest, evaluate_random_forest),
    'XGBoost': (train_xgboost, evaluate_xgboost),
    'SVR': (train_svr, evaluate_svr),
    # 'LSTM': (train_lstm, evaluate_lstm)  # Commented out due to TensorFlow issues
}

results = {}
for name, (train_func, eval_func) in models.items():
    if name == 'LSTM':
        train_func(X_train, y_train)
        results[name] = eval_func(X_test, y_test)
    else:
        train_func(X_train, y_train)
        results[name] = eval_func(X_test, y_test)

# Print results
for model, metrics in results.items():
    print(f"{model}: {metrics}")

# Select best based on RMSE
best_model = min(results, key=lambda x: results[x]['RMSE'])
print(f"Best model: {best_model}")