import joblib
import os
import numpy as np
import warnings
from sklearn.preprocessing import MinMaxScaler
from src.evaluate import evaluate_model

# Suppress TensorFlow/Keras warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

def create_sequences(data, seq_length=30):
    """Create sequences for LSTM."""
    X, y = [], []
    for i in range(len(data) - seq_length):
        X.append(data[i:i+seq_length])
        y.append(data[i+seq_length])
    return np.array(X), np.array(y)

def train_lstm(X, y, seq_length=30, model_path=None, scaler_path=None):
    """Train LSTM model."""
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
    
    model_dir = os.path.dirname(__file__)
    if model_path is None:
        model_path = os.path.join(model_dir, 'lstm.keras')
    if scaler_path is None:
        scaler_path = os.path.join(model_dir, 'lstm_scaler.pkl')
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    scaler = MinMaxScaler()
    y_scaled = scaler.fit_transform(y.reshape(-1, 1)).flatten()
    X_seq, y_seq = create_sequences(y_scaled, seq_length)
    X_seq = X_seq.reshape((X_seq.shape[0], X_seq.shape[1], 1))

    model = Sequential([
        Input(shape=(seq_length, 1)),
        LSTM(50, return_sequences=True),
        Dropout(0.2),
        LSTM(50),
        Dropout(0.2),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    model.fit(X_seq, y_seq, epochs=10, batch_size=32, verbose=0)
    model.save(model_path)
    joblib.dump(scaler, scaler_path)
    return model, scaler

def predict_lstm(X, seq_length=30, model_path=None, scaler_path=None):
    """Predict using LSTM.
    
    Args:
        X: Sequential data (array of prices), e.g., last 30 Close prices
    """
    from tensorflow.keras.models import load_model
    
    model_dir = os.path.dirname(__file__)
    if model_path is None:
        model_path = os.path.join(model_dir, 'lstm.keras')
    if scaler_path is None:
        scaler_path = os.path.join(model_dir, 'lstm_scaler.pkl')
    
    # Clean up old HDF5 files
    h5_path = model_path.replace('.keras', '.h5')
    if os.path.exists(h5_path):
        os.remove(h5_path)
    
    # Check if model file exists; if not, train a new one
    if not os.path.exists(model_path):
        # Model not found; train it
        _, _ = train_lstm(X, X, seq_length, model_path, scaler_path)
    
    try:
        model = load_model(model_path)
    except Exception:
        # If loading fails, retrain
        _, model = train_lstm(X, X, seq_length, model_path, scaler_path)
    
    scaler = joblib.load(scaler_path)
    # Use last seq_length values from X
    if len(X) < seq_length:
        # Pad with first value if not enough data
        X_seq = np.concatenate([np.full(seq_length - len(X), X[0]), X])
    else:
        X_seq = X[-seq_length:]
    
    X_seq = X_seq.reshape((1, seq_length, 1))
    pred_scaled = model.predict(X_seq, verbose=0)
    return scaler.inverse_transform(pred_scaled).flatten()

def evaluate_lstm(X_test, y_test, seq_length=30, model_path=None, scaler_path=None):
    """Evaluate LSTM model."""
    from tensorflow.keras.models import load_model
    
    model_dir = os.path.dirname(__file__)
    if model_path is None:
        model_path = os.path.join(model_dir, 'lstm.keras')
    if scaler_path is None:
        scaler_path = os.path.join(model_dir, 'lstm_scaler.pkl')
    
    try:
        # Remove old model files if they exist to avoid deserialization errors
        if os.path.exists(model_path) and model_path.endswith('.h5'):
            os.remove(model_path)
            model_path = model_path.replace('.h5', '.keras')
        if os.path.exists(scaler_path):
            try:
                joblib.load(scaler_path)
            except Exception:
                os.remove(scaler_path)
        
        model = load_model(model_path)
        scaler = joblib.load(scaler_path)
        
        # Create sequences from test data
        X_seq, y_seq = create_sequences(y_test, seq_length)
        X_seq = X_seq.reshape((X_seq.shape[0], X_seq.shape[1], 1))
        
        if len(X_seq) == 0:
            # Not enough test data for sequences; use last prediction
            y_pred = predict_lstm(y_test, seq_length, model_path, scaler_path)
            return evaluate_model(y_test[-1:], y_pred)
        
        # Predict on all test sequences
        y_pred_scaled = model.predict(X_seq, verbose=0)
        y_pred = scaler.inverse_transform(y_pred_scaled).flatten()
        
        # Compare with actual test values (aligned with sequences)
        y_actual = y_test[seq_length:seq_length+len(y_pred)]
        
        if len(y_actual) > 0 and len(y_pred) > 0:
            return evaluate_model(y_actual, y_pred)
        else:
            # Fallback to single prediction
            y_pred = predict_lstm(y_test, seq_length, model_path, scaler_path)
            return evaluate_model(y_test[-1:], y_pred)
    except Exception as e:
        print(f"LSTM evaluation error: {e}")
        # Return NaN results if evaluation fails
        return {'MAE': float('nan'), 'RMSE': float('nan'), 'MAPE': float('nan'), 'R2': float('nan'), 'Directional_Accuracy': float('nan')}
