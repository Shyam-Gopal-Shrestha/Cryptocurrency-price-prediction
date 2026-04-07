# 🚀 How to Run Model Training Outside Notebooks

## Quick Start (TL;DR)

**Option A: Python Script (Fastest)**

```bash
cd /Users/shyamshrestha/crypto-price-prediction
/opt/anaconda3/envs/crypto_env/bin/python train_models.py
```

**Option B: Bash Script**

```bash
cd /Users/shyamshrestha/crypto-price-prediction
./run_training.sh
```

**Option C: Simple Python Script**

```bash
/opt/anaconda3/envs/crypto_env/bin/python quick_train.py
```

---

## Detailed Methods

### 1️⃣ Method: train_models.py (Recommended)

**What it is:** Full-featured training script with progress indicators and detailed output

**Location:** `/Users/shyamshrestha/crypto-price-prediction/train_models.py`

**How to run:**

```bash
cd /Users/shyamshrestha/crypto-price-prediction
/opt/anaconda3/envs/crypto_env/bin/python train_models.py
```

**Features:**

- ✓ Trains all 5 models (Linear Regression, Random Forest, XGBoost, SVR, LSTM)
- ✓ Shows progress with emoji feedback (✓/✗)
- ✓ Displays formatted results table
- ✓ Identifies best model
- ✓ Error handling per model

**Output Example:**

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

### 2️⃣ Method: run_training.sh (Bash Wrapper)

**What it is:** Simple bash script that calls train_models.py

**Location:** `/Users/shyamshrestha/crypto-price-prediction/run_training.sh`

**How to run:**

```bash
cd /Users/shyamshrestha/crypto-price-prediction
./run_training.sh
```

**Or with full path:**

```bash
/Users/shyamshrestha/crypto-price-prediction/run_training.sh
```

---

### 3️⃣ Method: quick_train.py (Simple Alternative)

**What it is:** Lightweight Python script with nice formatting

**Location:** `/Users/shyamshrestha/crypto-price-prediction/quick_train.py`

**How to run:**

```bash
/opt/anaconda3/envs/crypto_env/bin/python quick_train.py
```

**Features:**

- ✓ Simple and readable code
- ✓ Less verbose output
- ✓ Same model comparison results

---

### 4️⃣ Method: API Endpoints (For Web Integration)

**What it is:** FastAPI endpoints for programmatic access

**How to start API server:**

```bash
cd /Users/shyamshrestha/crypto-price-prediction
uvicorn api.main:app --reload
```

**Start Training (returns immediately):**

```bash
curl -X POST http://localhost:8000/train/models
```

**Check Training Status:**

```bash
curl http://localhost:8000/train/status
```

**Get Results When Done:**

```bash
curl http://localhost:8000/models/comparison
```

**Available Endpoints:**

- `POST /train/models` - Start background training
- `GET /train/status` - Check training progress
- `GET /models/comparison` - Get latest results

---

## File Management

### Trained Model Files

All trained models are automatically saved to `src/models/`:

- `linear_regression.pkl` (sklearn pickle)
- `random_forest.pkl` (sklearn pickle)
- `xgboost.pkl` (sklearn pickle)
- `svr.pkl` (sklearn pickle)
- `lstm.keras` (Keras native format)
- `lstm_scaler.pkl` (data scaler for LSTM)

### Clear Old Models

```bash
rm -f src/models/*.pkl src/models/*.keras
```

---

## Environment Setup

### Required: crypto_env

All scripts automatically use `crypto_env` which has TensorFlow installed. If you get errors:

**Activate the environment manually:**

```bash
source /opt/anaconda3/bin/activate crypto_env
python train_models.py
conda deactivate
```

**Or use full Python path:**

```bash
/opt/anaconda3/envs/crypto_env/bin/python train_models.py
```

---

## Common Commands

| Task                          | Command                                                     |
| ----------------------------- | ----------------------------------------------------------- |
| Quick training                | `/opt/anaconda3/envs/crypto_env/bin/python train_models.py` |
| Bash wrapper                  | `./run_training.sh`                                         |
| Simple version                | `/opt/anaconda3/envs/crypto_env/bin/python quick_train.py`  |
| Start API                     | `uvicorn api.main:app --reload`                             |
| Start API (background)        | `nohup uvicorn api.main:app > api.log 2>&1 &`               |
| Clear old models              | `rm -f src/models/*.pkl src/models/*.keras`                 |
| Check job status (if running) | `jobs`                                                      |
| Kill API                      | `pkill -f "uvicorn api.main:app"`                           |

---

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'tensorflow'`

**Solution:** Use the full path to crypto_env python:

```bash
/opt/anaconda3/envs/crypto_env/bin/python train_models.py
```

### Issue: `FileNotFoundError: BTC-USD historical data not found`

**Solution:** The script auto-downloads data. Just run it, it will fetch automatically.

### Issue: Segmentation Fault with base Python

**Solution:** Never use base `python` command. Always use:

```bash
/opt/anaconda3/envs/crypto_env/bin/python
```

### Issue: API port 8000 already in use

**Solution:** Use different port:

```bash
uvicorn api.main:app --port 8001 --reload
```

---

## Next Steps

1. **Run training:** Choose any method above
2. **Check models:** List files in `src/models/`
3. **View results:** Output table shows metrics for all models
4. **Deploy:** Use API endpoints for production integration
5. **Custom training:** Edit `train_models.py` to modify parameters

---

## Integration Examples

### Python Script Integration

```python
import subprocess
result = subprocess.run([
    '/opt/anaconda3/envs/crypto_env/bin/python',
    'train_models.py'
], capture_output=True, text=True)
print(result.stdout)
```

### Shell Script Integration

```bash
#!/bin/bash
cd /Users/shyamshrestha/crypto-price-prediction
/opt/anaconda3/envs/crypto_env/bin/python train_models.py | tee training_log.txt
```

### Scheduled Training (Cron)

```bash
# Add to crontab: crontab -e
0 2 * * * cd /Users/shyamshrestha/crypto-price-prediction && /opt/anaconda3/envs/crypto_env/bin/python train_models.py >> training_$(date +\%Y\%m\%d).log 2>&1
```

---

**That's it! Choose the method that works best for your use case.** 🎉
