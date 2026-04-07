import joblib
import os
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from src.evaluate import evaluate_model

def train_linear_regression(X, y, model_path=None):
    """Train Linear Regression model."""
    if model_path is None:
        model_path = os.path.join(os.path.dirname(__file__), '../../models/linear_regression.pkl')
    model = LinearRegression()
    model.fit(X, y)
    joblib.dump(model, model_path)
    return model

def predict_linear_regression(X, model_path=None):
    """Predict using Linear Regression."""
    if model_path is None:
        model_path = os.path.join(os.path.dirname(__file__), '../../models/linear_regression.pkl')
    model = joblib.load(model_path)
    return model.predict(X)

def evaluate_linear_regression(X_test, y_test, model_path=None):
    """Evaluate Linear Regression."""
    if model_path is None:
        model_path = os.path.join(os.path.dirname(__file__), '../../models/linear_regression.pkl')
    y_pred = predict_linear_regression(X_test, model_path)
    return evaluate_model(y_test, y_pred)