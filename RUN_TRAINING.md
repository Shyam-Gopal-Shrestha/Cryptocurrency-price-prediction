# Run Model Training - 3 Methods

## Method 1: Standalone Python Script (Recommended for local testing)

The simplest way to train all models outside the notebook:

```bash
# Navigate to project root
cd /Users/shyamshrestha/crypto-price-prediction

# Run with crypto_env (stable TensorFlow)
/opt/anaconda3/envs/crypto_env/bin/python train_models.py
```

**What it does:**

- Loads BTC-USD historical data
- Trains 5 models: Linear Regression, Random Forest, XGBoost, SVR, LSTM
- Compares metrics (MAE, RMSE, MAPE, R², Directional Accuracy)
- Displays results table
- Identifies best model by RMSE

**Output:**

```
Training models...
  Training Linear Regression... ✓
  Training Random Forest... ✓
  Training XGBoost... ✓
  Training SVR... ✓
  Training LSTM... ✓

================================================================================
MODEL COMPARISON RESULTS
================================================================================
                            MAE           RMSE        MAPE         R2  Directional_Accuracy
Linear Regression     456.241656     687.587848    0.688838   0.999529         80.275974
Random Forest       13020.299308   21694.318277   13.213736   0.531034         46.590909
XGBoost             14214.002321   22981.248978   15.083648   0.473745         54.139610
SVR                 56640.397134   64964.048771   82.971648  -3.205286        46.834416
LSTM               184354.116752  122737.320513  279.803303 -14.520767         0.000000
================================================================================

✓ Best model: Linear Regression (RMSE: 687.59)
Done!
```

---

## Method 2: Bash Script

Use the convenience wrapper script:

```bash
cd /Users/shyamshrestha/crypto-price-prediction
./run_training.sh
```

This automatically runs with `crypto_env`.

---

## Method 3: API Endpoints (Recommended for production/web)

Start the FastAPI server:

```bash
cd /Users/shyamshrestha/crypto-price-prediction
uvicorn api.main:app --reload
```

Then use these endpoints:

### Start Training (Background)

```bash
curl -X POST http://localhost:8000/train/models
```

Response:

```json
{
  "status": "started",
  "message": "Model training started. Check /train/status for progress."
}
```

### Check Training Status

```bash
curl http://localhost:8000/train/status
```

Response (while training):

```json
{
  "is_running": true,
  "progress": "Training LSTM...",
  "results": null
}
```

Response (after training):

```json
{
  "is_running": false,
  "progress": "Training complete!",
  "results": {
    "Linear Regression": {
      "MAE": 456.24,
      "RMSE": 687.59,
      "MAPE": 0.69,
      "R2": 0.9995,
      "Directional_Accuracy": 80.28
    },
    ...
  }
}
```

### Get Model Comparison Results

```bash
curl http://localhost:8000/models/comparison
```

---

## Model Files Location

Trained model files are saved to:

- `src/models/linear_regression.pkl`
- `src/models/random_forest.pkl`
- `src/models/xgboost.pkl`
- `src/models/svr.pkl`
- `src/models/lstm.keras` (and `lstm_scaler.pkl`)

---

## Which Method to Use?

| Method            | Use Case                    | Speed    | Output                           |
| ----------------- | --------------------------- | -------- | -------------------------------- |
| **Python Script** | Local testing, CI/CD        | ~2-3 min | Console table                    |
| **Bash Script**   | Quick training run          | ~2-3 min | Console table                    |
| **API Endpoints** | Production, web integration | ~2-3 min | JSON results + progress tracking |

---

## Troubleshooting

**Issue: Segmentation fault with base Python**

- Solution: Always use `/opt/anaconda3/envs/crypto_env/bin/python` or the API which uses the correct environment

**Issue: TensorFlow import errors**

- Solution: Run from project root directory, not from subdirectories

**Issue: Data file not found**

- Solution: The script automatically runs `fetch_historical.py` if needed

---

## Next Steps

1. **For predictions on new data**: See `api/main.py` `/predict` endpoint
2. **For custom training parameters**: Edit `train_models.py` lines 25-45
3. **For model deployment**: Models are persisted automatically in `src/models/`
