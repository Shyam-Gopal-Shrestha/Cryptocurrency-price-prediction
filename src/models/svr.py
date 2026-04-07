import joblib
import os
from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler
from src.evaluate import evaluate_model

def train_svr(X, y, model_path=None, scaler_path=None):
    """Train SVR model with scaling."""
    if model_path is None:
        model_path = os.path.join(os.path.dirname(__file__), '../../models/svr.pkl')
    if scaler_path is None:
        scaler_path = os.path.join(os.path.dirname(__file__), '../../models/svr_scaler.pkl')
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    model = SVR(kernel='rbf')
    model.fit(X_scaled, y)
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)
    return model, scaler

def predict_svr(X, model_path=None, scaler_path=None):
    """Predict using SVR."""
    if model_path is None:
        model_path = os.path.join(os.path.dirname(__file__), '../../models/svr.pkl')
    if scaler_path is None:
        scaler_path = os.path.join(os.path.dirname(__file__), '../../models/svr_scaler.pkl')
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    X_scaled = scaler.transform(X)
    return model.predict(X_scaled)

def evaluate_svr(X_test, y_test, model_path=None, scaler_path=None):
    """Evaluate SVR."""
    if model_path is None:
        model_path = os.path.join(os.path.dirname(__file__), '../../models/svr.pkl')
    if scaler_path is None:
        scaler_path = os.path.join(os.path.dirname(__file__), '../../models/svr_scaler.pkl')
    y_pred = predict_svr(X_test, model_path, scaler_path)
    return evaluate_model(y_test, y_pred)