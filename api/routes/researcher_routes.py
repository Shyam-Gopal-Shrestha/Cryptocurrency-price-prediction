import json
import sqlite3
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.neural_network import MLPRegressor
from sklearn.svm import SVR

from api.core.runtime import (
    HAS_XGBOOST,
    MODEL_STORAGE_DIR,
    build_features,
    compute_metrics,
    get_connection,
    get_symbol_dataframe,
    normalize_symbol,
    now_utc,
    require_role,
    track_activity,
    track_api_usage,
)
from api.schemas.requests import DataFetchRequest, PreprocessRequest, TrainRequest

try:
    from xgboost import XGBRegressor
except Exception:  # pragma: no cover
    XGBRegressor = None  # pragma: no cover

router = APIRouter(tags=["platform"])


@router.get("/researcher/config")
def researcher_config(researcher: sqlite3.Row = Depends(require_role("researcher", "admin"))):
    conn = get_connection()
    try:
        cryptos = conn.execute(
            "SELECT symbol, name FROM crypto_configs WHERE is_enabled = 1 ORDER BY symbol"
        ).fetchall()
        models = conn.execute(
            """
            SELECT model_name
            FROM model_configs
            WHERE is_enabled = 1 AND is_researcher_available = 1
            ORDER BY model_name
            """
        ).fetchall()
    finally:
        conn.close()

    return {
        "cryptocurrencies": [dict(c) for c in cryptos],
        "models": [m["model_name"] for m in models],
    }


@router.post("/researcher/fetch-data")
def researcher_fetch_data(
    payload: DataFetchRequest,
    researcher: sqlite3.Row = Depends(require_role("researcher", "admin")),
):
    symbol = normalize_symbol(payload.symbol)
    df = yf.download(
        symbol,
        start=payload.start_date,
        end=payload.end_date,
        interval=payload.interval,
        progress=False,
        auto_adjust=False,
    )
    track_api_usage("yfinance", "download", researcher["id"])

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="No data returned from Yahoo Finance.")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    df = df.reset_index()
    df.columns = [str(c).lower() for c in df.columns]
    if "date" in df.columns:
        df = df.rename(columns={"date": "timestamp"})
    elif "datetime" in df.columns:
        df = df.rename(columns={"datetime": "timestamp"})

    expected = {"timestamp", "open", "high", "low", "close", "volume"}
    if not expected.issubset(set(df.columns)):
        raise HTTPException(status_code=500, detail="Unexpected Yahoo Finance response columns.")

    conn = get_connection()
    inserted = 0
    try:
        for _, row in df.iterrows():
            conn.execute(
                """
                INSERT OR IGNORE INTO historical_prices
                (symbol, timestamp, open, high, low, close, volume, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'yfinance', ?)
                """,
                (
                    symbol,
                    pd.to_datetime(row["timestamp"]).isoformat(),
                    float(row["open"]) if not pd.isna(row["open"]) else None,
                    float(row["high"]) if not pd.isna(row["high"]) else None,
                    float(row["low"]) if not pd.isna(row["low"]) else None,
                    float(row["close"]) if not pd.isna(row["close"]) else None,
                    float(row["volume"]) if not pd.isna(row["volume"]) else None,
                    now_utc(),
                ),
            )
            inserted += 1
        conn.commit()
    finally:
        conn.close()

    track_activity(researcher["id"], "researcher.fetch_data", f"symbol={symbol}, rows={inserted}")
    return {"message": "Historical data fetched and stored.", "symbol": symbol, "rows": inserted}


@router.post("/researcher/preprocess")
def researcher_preprocess(
    payload: PreprocessRequest,
    researcher: sqlite3.Row = Depends(require_role("researcher", "admin")),
):
    symbol = normalize_symbol(payload.symbol)
    raw_df = get_symbol_dataframe(symbol)

    if raw_df.empty:
        raise HTTPException(status_code=400, detail="No data available.")

    before_rows = len(raw_df)
    features_df = build_features(raw_df, payload.fast_window, payload.slow_window)
    after_rows = len(features_df)

    track_activity(
        researcher["id"],
        "researcher.preprocess",
        f"symbol={symbol}, before={before_rows}, after={after_rows}",
    )

    preview_cols = ["timestamp", "close", "ma_fast", "ma_slow", "rsi", "macd", "volatility"]
    preview = features_df.tail(10)[preview_cols].copy()
    preview["timestamp"] = preview["timestamp"].dt.strftime("%Y-%m-%d")

    return {
        "symbol": symbol,
        "rows_before": before_rows,
        "rows_after": after_rows,
        "missing_values_removed": before_rows - after_rows,
        "preview": preview.to_dict(orient="records"),
    }


@router.post("/researcher/train")
def researcher_train_models(
    payload: TrainRequest,
    researcher: sqlite3.Row = Depends(require_role("researcher", "admin")),
):
    symbol = normalize_symbol(payload.symbol)
    if payload.horizon < 1 or payload.horizon > 30:
        raise HTTPException(status_code=400, detail="Horizon must be between 1 and 30.")
    if payload.test_size <= 0 or payload.test_size >= 0.5:
        raise HTTPException(status_code=400, detail="test_size must be in (0, 0.5).")

    conn = get_connection()
    try:
        allowed_models = {
            row["model_name"]
            for row in conn.execute(
                """
                SELECT model_name FROM model_configs
                WHERE is_enabled = 1 AND is_researcher_available = 1
                """
            ).fetchall()
        }
    finally:
        conn.close()

    requested_models = [m.strip().lower() for m in payload.models]
    disallowed = [m for m in requested_models if m not in allowed_models]
    if disallowed:
        raise HTTPException(status_code=400, detail=f"Models not allowed: {disallowed}")

    raw_df = get_symbol_dataframe(symbol)
    features_df = build_features(raw_df)
    if len(features_df) < 100:
        raise HTTPException(status_code=400, detail="Not enough rows after preprocessing.")

    features_df["target"] = features_df["close"].shift(-payload.horizon)
    features_df = features_df.dropna().reset_index(drop=True)

    feature_cols = ["open", "high", "low", "close", "volume", "ma_fast", "ma_slow", "rsi", "macd", "volatility"]
    X = features_df[feature_cols].values
    y = features_df["target"].values

    split_idx = int(len(features_df) * (1 - payload.test_size))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    model_factories = {
        "linear_regression": lambda: LinearRegression(),
        "random_forest": lambda: RandomForestRegressor(n_estimators=300, random_state=42),
        "svr": lambda: SVR(C=10.0, epsilon=0.01, gamma="scale"),
        "lstm": lambda: MLPRegressor(
            hidden_layer_sizes=(128, 64),
            activation="tanh",
            solver="adam",
            max_iter=800,
            random_state=42,
        ),
        "gru": lambda: MLPRegressor(
            hidden_layer_sizes=(96, 48),
            activation="relu",
            solver="adam",
            max_iter=800,
            random_state=42,
        ),
        "transformer": lambda: GradientBoostingRegressor(
            n_estimators=400,
            learning_rate=0.03,
            max_depth=3,
            random_state=42,
        ),
    }
    if HAS_XGBOOST and XGBRegressor is not None:
        model_factories["xgboost"] = lambda: XGBRegressor(
            n_estimators=400,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
        )
    else:
        model_factories["xgboost"] = lambda: GradientBoostingRegressor(
            n_estimators=500,
            learning_rate=0.03,
            max_depth=4,
            random_state=42,
        )

    results = []
    best = None

    for model_name in requested_models:
        if model_name not in model_factories:
            results.append(
                {
                    "model": model_name,
                    "status": "skipped",
                    "reason": "Model implementation is not available in this runtime.",
                }
            )
            continue

        model = model_factories[model_name]()
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        metrics = compute_metrics(y_test, preds)

        residual_std = float(np.std(y_test - preds)) if len(preds) else 0.0
        artifact_name = f"{symbol}_{model_name}_{int(datetime.now().timestamp())}.joblib"
        artifact_path = MODEL_STORAGE_DIR / artifact_name
        joblib.dump(
            {
                "model": model,
                "feature_cols": feature_cols,
                "residual_std": residual_std,
                "horizon": payload.horizon,
            },
            artifact_path,
        )

        conn = get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO experiments
                (researcher_id, symbol, model_name, metrics_json, artifact_path, status, is_deployed, created_at)
                VALUES (?, ?, ?, ?, ?, 'trained', 0, ?)
                """,
                (
                    researcher["id"],
                    symbol,
                    model_name,
                    json.dumps(metrics),
                    str(artifact_path),
                    now_utc(),
                ),
            )
            conn.commit()
            experiment_id = cursor.lastrowid
        finally:
            conn.close()

        result = {
            "experiment_id": experiment_id,
            "model": model_name,
            "status": "trained",
            "metrics": metrics,
            "artifact_path": str(artifact_path),
        }
        results.append(result)

        if best is None or metrics["rmse"] < best["metrics"]["rmse"]:
            best = result

    if payload.auto_deploy_best and best:
        conn = get_connection()
        try:
            conn.execute("UPDATE experiments SET is_deployed = 0 WHERE symbol = ?", (symbol,))
            conn.execute("UPDATE experiments SET is_deployed = 1, status = 'deployed' WHERE id = ?", (best["experiment_id"],))
            conn.commit()
        finally:
            conn.close()
        best["auto_deployed"] = True

    track_activity(researcher["id"], "researcher.train", f"symbol={symbol}, models={requested_models}")
    return {"symbol": symbol, "results": results, "best_model": best}


@router.post("/researcher/deploy/{experiment_id}")
def researcher_deploy_model(
    experiment_id: int,
    researcher: sqlite3.Row = Depends(require_role("researcher", "admin")),
):
    conn = get_connection()
    try:
        exp = conn.execute(
            "SELECT id, symbol, model_name FROM experiments WHERE id = ?",
            (experiment_id,),
        ).fetchone()
        if not exp:
            raise HTTPException(status_code=404, detail="Experiment not found.")

        conn.execute("UPDATE experiments SET is_deployed = 0 WHERE symbol = ?", (exp["symbol"],))
        conn.execute("UPDATE experiments SET is_deployed = 1, status = 'deployed' WHERE id = ?", (experiment_id,))
        conn.commit()
    finally:
        conn.close()

    track_activity(researcher["id"], "researcher.deploy", f"experiment_id={experiment_id}")
    return {
        "message": "Model deployed.",
        "experiment_id": experiment_id,
        "symbol": exp["symbol"],
        "model": exp["model_name"],
    }


@router.get("/researcher/experiments")
def researcher_experiments(researcher: sqlite3.Row = Depends(require_role("researcher", "admin"))):
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, researcher_id, symbol, model_name, metrics_json, artifact_path, status, is_deployed, created_at
            FROM experiments
            ORDER BY datetime(created_at) DESC
            LIMIT 200
            """
        ).fetchall()
    finally:
        conn.close()

    results = []
    for r in rows:
        item = dict(r)
        item["metrics"] = json.loads(item.pop("metrics_json"))
        item["is_deployed"] = bool(item["is_deployed"])
        results.append(item)
    return results