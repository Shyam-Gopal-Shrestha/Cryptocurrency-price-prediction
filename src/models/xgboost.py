import joblib
import os
from xgboost import XGBRegressor
from src.evaluate import evaluate_model

def train_xgboost(X, y, model_path=None):
    """Train XGBoost model."""
    if model_path is None:
        model_path = os.path.join(os.path.dirname(__file__), '../../models/xgboost.pkl')
    model = XGBRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    joblib.dump(model, model_path)
    return model

def predict_xgboost(X, model_path=None):
    """Predict using XGBoost."""
    if model_path is None:
        model_path = os.path.join(os.path.dirname(__file__), '../../models/xgboost.pkl')
    model = joblib.load(model_path)
    return model.predict(X)

def evaluate_xgboost(X_test, y_test, model_path=None):
    """Evaluate XGBoost."""
    if model_path is None:
        model_path = os.path.join(os.path.dirname(__file__), '../../models/xgboost.pkl')
    y_pred = predict_xgboost(X_test, model_path)
    return evaluate_model(y_test, y_pred)