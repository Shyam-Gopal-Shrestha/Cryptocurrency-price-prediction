import joblib
import os
from sklearn.ensemble import RandomForestRegressor
from src.evaluate import evaluate_model

def train_random_forest(X, y, model_path=None):
    """Train Random Forest model."""
    if model_path is None:
        model_path = os.path.join(os.path.dirname(__file__), '../../models/random_forest.pkl')
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    joblib.dump(model, model_path)
    return model

def predict_random_forest(X, model_path=None):
    """Predict using Random Forest."""
    if model_path is None:
        model_path = os.path.join(os.path.dirname(__file__), '../../models/random_forest.pkl')
    model = joblib.load(model_path)
    return model.predict(X)

def evaluate_random_forest(X_test, y_test, model_path=None):
    """Evaluate Random Forest."""
    if model_path is None:
        model_path = os.path.join(os.path.dirname(__file__), '../../models/random_forest.pkl')
    y_pred = predict_random_forest(X_test, model_path)
    return evaluate_model(y_test, y_pred)