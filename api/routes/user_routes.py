import json
import math
import sqlite3
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from api.core.runtime import (
    build_features,
    build_risk_note,
    compute_risk_profile,
    evaluate_alert_condition,
    generate_explanation,
    get_connection,
    get_gemini_api_key,
    get_latest_price_and_change,
    get_symbol_dataframe,
    normalize_symbol,
    now_utc,
    require_role,
    track_activity,
    track_api_usage,
)
from api.schemas.requests import (
    AlertCreateRequest,
    AlertUpdateRequest,
    ChatRequest,
    PortfolioHoldingRequest,
    PredictionRequest,
)

router = APIRouter(tags=["platform"])


@router.get("/user/config")
def user_config(current_user: sqlite3.Row = Depends(require_role("user", "researcher", "admin"))):
    conn = get_connection()
    try:
        cryptos = conn.execute(
            "SELECT symbol, name FROM crypto_configs WHERE is_enabled = 1 ORDER BY symbol"
        ).fetchall()
    finally:
        conn.close()
    return {"cryptocurrencies": [dict(c) for c in cryptos], "max_horizon": 30}


@router.post("/user/predict")
def user_predict(
    payload: PredictionRequest,
    current_user: sqlite3.Row = Depends(require_role("user", "researcher", "admin")),
):
    symbol = normalize_symbol(payload.symbol)
    if payload.horizon < 1 or payload.horizon > 30:
        raise HTTPException(status_code=400, detail="Horizon must be in range 1-30 days.")
    mode = payload.explanation_mode.strip().lower()
    if mode not in {"simple", "technical"}:
        raise HTTPException(status_code=400, detail="explanation_mode must be simple or technical.")
    risk_tolerance = (payload.risk_tolerance or "medium").strip().lower()
    if risk_tolerance not in {"low", "medium", "high"}:
        raise HTTPException(status_code=400, detail="risk_tolerance must be low, medium, or high.")

    conn = get_connection()
    try:
        deployed = conn.execute(
            """
            SELECT id, model_name, artifact_path
            FROM experiments
            WHERE symbol = ? AND is_deployed = 1
            ORDER BY datetime(created_at) DESC
            LIMIT 1
            """,
            (symbol,),
        ).fetchone()
    finally:
        conn.close()

    raw_df = get_symbol_dataframe(symbol)
    feature_df = build_features(raw_df)
    if feature_df.empty:
        raise HTTPException(status_code=400, detail="Not enough feature rows.")

    risk_score, risk_level = compute_risk_profile(raw_df)
    risk_note = build_risk_note(risk_level, risk_tolerance)

    last_row = feature_df.iloc[-1]
    last_close = float(last_row["close"])

    if not deployed:
        predicted = last_close
        model_name = "fallback"
        confidence = 50.0
    else:
        artifact = joblib.load(deployed["artifact_path"])
        model = artifact["model"]
        feature_cols = artifact["feature_cols"]
        x_last = feature_df[feature_cols].iloc[-1].values.reshape(1, -1)
        predicted = float(model.predict(x_last)[0])
        drift = (predicted - last_close) / max(last_close, 1e-6)
        predicted = float(last_close * (1 + drift * payload.horizon))
        residual_std = float(artifact.get("residual_std", 0.0))
        uncertainty_ratio = min((residual_std / max(last_close, 1e-6)), 1.0)
        confidence = max(5.0, 100.0 * (1.0 - uncertainty_ratio))
        model_name = deployed["model_name"]

    trend = "bullish" if predicted >= last_close else "bearish"
    explanation, explanation_provider = generate_explanation(
        symbol,
        payload.horizon,
        predicted,
        trend,
        confidence,
        mode,
        last_close,
    )
    track_api_usage("internal", "prediction", current_user["id"])
    track_api_usage(explanation_provider, "explanation", current_user["id"])

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO prediction_history
            (user_id, symbol, horizon, predicted_price, trend, confidence, explanation_mode, explanation, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                current_user["id"],
                symbol,
                payload.horizon,
                predicted,
                trend,
                confidence,
                mode,
                explanation,
                now_utc(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    track_activity(current_user["id"], "user.predict", f"symbol={symbol}, horizon={payload.horizon}")

    return {
        "symbol": symbol,
        "horizon": payload.horizon,
        "model": model_name,
        "last_close": last_close,
        "predicted_price": predicted,
        "trend": trend,
        "confidence": confidence,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_tolerance": risk_tolerance,
        "risk_note": risk_note,
        "explanation_mode": mode,
        "explanation": explanation,
    }


@router.get("/user/predictions/history")
def user_prediction_history(current_user: sqlite3.Row = Depends(require_role("user", "researcher", "admin"))):
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, symbol, horizon, predicted_price, trend, confidence, explanation_mode, explanation, created_at
            FROM prediction_history
            WHERE user_id = ?
            ORDER BY datetime(created_at) DESC
            LIMIT 100
            """,
            (current_user["id"],),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


@router.get("/user/alerts")
def list_user_alerts(current_user: sqlite3.Row = Depends(require_role("user", "researcher", "admin"))):
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, symbol, alert_type, threshold_value, direction, sentiment_label, is_enabled,
                   email_enabled, last_notified_at, created_at
            FROM alerts
            WHERE user_id = ?
            ORDER BY datetime(created_at) DESC
            """,
            (current_user["id"],),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            **dict(r),
            "is_enabled": bool(r["is_enabled"]),
            "email_enabled": bool(r["email_enabled"]),
        }
        for r in rows
    ]


@router.post("/user/alerts")
def create_user_alert(
    payload: AlertCreateRequest,
    current_user: sqlite3.Row = Depends(require_role("user", "researcher", "admin")),
):
    symbol = normalize_symbol(payload.symbol)
    alert_type = (payload.alert_type or "target").strip().lower()
    if alert_type not in {"target", "percent", "sentiment"}:
        raise HTTPException(status_code=400, detail="alert_type must be target, percent, or sentiment.")

    direction = (payload.direction or "above").strip().lower()
    if direction not in {"above", "below"}:
        raise HTTPException(status_code=400, detail="direction must be above or below.")

    threshold_value = payload.threshold_value
    sentiment_label = (payload.sentiment_label or "").strip().lower() or None

    if alert_type in {"target", "percent"} and threshold_value is None:
        raise HTTPException(status_code=400, detail="threshold_value is required for target/percent alerts.")
    if alert_type == "sentiment" and sentiment_label not in {"positive", "neutral", "negative"}:
        raise HTTPException(status_code=400, detail="sentiment_label must be positive, neutral, or negative.")

    if alert_type in {"target", "percent"}:
        try:
            threshold_value = float(threshold_value)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="threshold_value must be numeric.")

        if alert_type == "target" and threshold_value <= 0:
            raise HTTPException(status_code=400, detail="target threshold must be greater than 0.")

        if alert_type == "percent":
            threshold_value = abs(threshold_value)
            if threshold_value <= 0 or threshold_value > 100:
                raise HTTPException(
                    status_code=400,
                    detail="percent threshold must be between 0 and 100.",
                )

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO alerts (
                user_id, symbol, alert_type, threshold_value, direction, sentiment_label,
                is_enabled, email_enabled, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                current_user["id"],
                symbol,
                alert_type,
                threshold_value,
                direction,
                sentiment_label,
                int(payload.is_enabled),
                int(payload.email_enabled),
                now_utc(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    track_activity(current_user["id"], "user.alert.create", f"symbol={symbol}, type={alert_type}")
    return {"message": "Alert created.", "id": cursor.lastrowid}


@router.patch("/user/alerts/{alert_id}")
def update_user_alert(
    alert_id: int,
    payload: AlertUpdateRequest,
    current_user: sqlite3.Row = Depends(require_role("user", "researcher", "admin")),
):
    updates = []
    params: List[Any] = []

    if payload.is_enabled is not None:
        updates.append("is_enabled = ?")
        params.append(int(payload.is_enabled))
    if payload.email_enabled is not None:
        updates.append("email_enabled = ?")
        params.append(int(payload.email_enabled))
    if not updates:
        raise HTTPException(status_code=400, detail="No alert fields provided to update.")

    conn = get_connection()
    try:
        found = conn.execute(
            "SELECT id FROM alerts WHERE id = ? AND user_id = ?",
            (alert_id, current_user["id"]),
        ).fetchone()
        if not found:
            raise HTTPException(status_code=404, detail="Alert not found.")

        conn.execute(
            f"UPDATE alerts SET {', '.join(updates)} WHERE id = ? AND user_id = ?",
            (*params, alert_id, current_user["id"]),
        )
        conn.commit()
    finally:
        conn.close()

    return {"message": "Alert updated."}


@router.delete("/user/alerts/{alert_id}")
def delete_user_alert(
    alert_id: int,
    current_user: sqlite3.Row = Depends(require_role("user", "researcher", "admin")),
):
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM alerts WHERE id = ? AND user_id = ?",
            (alert_id, current_user["id"]),
        )
        conn.commit()
    finally:
        conn.close()

    return {"message": "Alert deleted."}


@router.get("/user/alerts/check")
def check_user_alerts(
    sentiment_label: Optional[str] = None,
    current_user: sqlite3.Row = Depends(require_role("user", "researcher", "admin")),
):
    normalized_sentiment = (sentiment_label or "").strip().lower() or None

    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, symbol, alert_type, threshold_value, direction, sentiment_label, is_enabled,
                   email_enabled, last_notified_at, created_at
            FROM alerts
            WHERE user_id = ? AND is_enabled = 1
            ORDER BY datetime(created_at) DESC
            """,
            (current_user["id"],),
        ).fetchall()
    finally:
        conn.close()

    checks = []
    triggered = []

    for r in rows:
        alert = dict(r)
        symbol = alert["symbol"]
        latest_price, pct_change_24h = get_latest_price_and_change(symbol)
        evaluation = evaluate_alert_condition(
            alert,
            latest_price=latest_price,
            pct_change_24h=pct_change_24h,
            sentiment_label=normalized_sentiment,
        )

        item = {
            **alert,
            "is_enabled": bool(alert["is_enabled"]),
            "email_enabled": bool(alert["email_enabled"]),
            **evaluation,
        }
        checks.append(item)
        if evaluation["is_triggered"]:
            triggered.append(item)

    return {
        "count": len(checks),
        "triggered_count": len(triggered),
        "alerts": checks,
        "triggered": triggered,
        "sentiment_label": normalized_sentiment,
    }


@router.get("/user/portfolio")
def get_user_portfolio(current_user: sqlite3.Row = Depends(require_role("user", "researcher", "admin"))):
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, symbol, quantity, avg_buy_price, created_at, updated_at
            FROM portfolio_holdings
            WHERE user_id = ?
            ORDER BY symbol ASC
            """,
            (current_user["id"],),
        ).fetchall()
    finally:
        conn.close()

    holdings: List[Dict[str, Any]] = []
    total_market_value = 0.0
    total_cost_basis = 0.0

    for r in rows:
        item = dict(r)
        symbol = item["symbol"]
        quantity = float(item["quantity"])
        avg_buy = float(item["avg_buy_price"])

        latest_price, _ = get_latest_price_and_change(symbol)
        market_price = float(latest_price) if latest_price is not None else avg_buy

        cost_basis = quantity * avg_buy
        market_value = quantity * market_price
        unrealized_pl = market_value - cost_basis
        unrealized_pl_pct = (unrealized_pl / max(cost_basis, 1e-6)) * 100.0

        risk_score = None
        risk_level = None
        try:
            raw_df = get_symbol_dataframe(symbol)
            rs, rl = compute_risk_profile(raw_df)
            risk_score = rs
            risk_level = rl
        except Exception:
            pass

        total_market_value += market_value
        total_cost_basis += cost_basis

        holdings.append(
            {
                **item,
                "market_price": market_price,
                "market_value": market_value,
                "cost_basis": cost_basis,
                "unrealized_pl": unrealized_pl,
                "unrealized_pl_pct": unrealized_pl_pct,
                "risk_score": risk_score,
                "risk_level": risk_level,
            }
        )

    for h in holdings:
        h["allocation_pct"] = (h["market_value"] / max(total_market_value, 1e-6)) * 100.0 if total_market_value > 0 else 0.0

    return {
        "holdings": holdings,
        "summary": {
            "total_market_value": total_market_value,
            "total_cost_basis": total_cost_basis,
            "total_unrealized_pl": total_market_value - total_cost_basis,
            "total_unrealized_pl_pct": ((total_market_value - total_cost_basis) / max(total_cost_basis, 1e-6)) * 100.0
            if total_cost_basis > 0
            else 0.0,
        },
    }


@router.post("/user/portfolio/holdings")
def upsert_user_holding(
    payload: PortfolioHoldingRequest,
    current_user: sqlite3.Row = Depends(require_role("user", "researcher", "admin")),
):
    symbol = normalize_symbol(payload.symbol)
    quantity = float(payload.quantity)
    avg_buy_price = float(payload.avg_buy_price)

    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM portfolio_holdings WHERE user_id = ? AND symbol = ?",
            (current_user["id"], symbol),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE portfolio_holdings
                SET quantity = ?, avg_buy_price = ?, updated_at = ?
                WHERE user_id = ? AND symbol = ?
                """,
                (quantity, avg_buy_price, now_utc(), current_user["id"], symbol),
            )
        else:
            conn.execute(
                """
                INSERT INTO portfolio_holdings (user_id, symbol, quantity, avg_buy_price, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (current_user["id"], symbol, quantity, avg_buy_price, now_utc(), now_utc()),
            )
        conn.commit()
    finally:
        conn.close()

    return {"message": "Holding saved.", "symbol": symbol}


@router.delete("/user/portfolio/holdings/{symbol}")
def delete_user_holding(
    symbol: str,
    current_user: sqlite3.Row = Depends(require_role("user", "researcher", "admin")),
):
    normalized = normalize_symbol(symbol)
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM portfolio_holdings WHERE user_id = ? AND symbol = ?",
            (current_user["id"], normalized),
        )
        conn.commit()
    finally:
        conn.close()

    return {"message": "Holding removed.", "symbol": normalized}


@router.get("/prediction-vs-actual")
def prediction_vs_actual(
    symbol: str = "BTC-USD",
    model: str = "random_forest",
    limit: int = 30,
    current_user: sqlite3.Row = Depends(require_role("user", "researcher", "admin")),
):
    symbol = normalize_symbol(symbol)
    model = model.strip().lower()
    limit = max(10, min(int(limit), 180))

    raw_df = get_symbol_dataframe(symbol)
    feature_df = build_features(raw_df)
    if len(feature_df) < 3:
        raise HTTPException(status_code=400, detail=f"Not enough data for {symbol}.")

    conn = get_connection()
    deployed = None
    try:
        deployed = conn.execute(
            """
            SELECT model_name, artifact_path
            FROM experiments
            WHERE symbol = ? AND is_deployed = 1 AND model_name = ?
            ORDER BY datetime(created_at) DESC
            LIMIT 1
            """,
            (symbol, model),
        ).fetchone()

        if not deployed:
            deployed = conn.execute(
                """
                SELECT model_name, artifact_path
                FROM experiments
                WHERE symbol = ? AND is_deployed = 1
                ORDER BY datetime(created_at) DESC
                LIMIT 1
                """,
                (symbol,),
            ).fetchone()
    finally:
        conn.close()

    model_obj = None
    feature_cols = None
    model_used = "fallback_naive"

    if deployed:
        try:
            artifact = joblib.load(deployed["artifact_path"])
            model_obj = artifact.get("model")
            feature_cols = artifact.get("feature_cols")
            if model_obj is not None and feature_cols:
                model_used = deployed["model_name"]
        except Exception:
            model_obj = None
            feature_cols = None
            model_used = "fallback_naive"

    eval_df = feature_df.tail(limit + 1).reset_index(drop=True)
    points: List[Dict[str, Any]] = []

    for index in range(len(eval_df) - 1):
        current_row = eval_df.iloc[index]
        next_row = eval_df.iloc[index + 1]

        actual = float(next_row["close"])
        predicted = float(current_row["close"])

        if model_obj is not None and feature_cols:
            try:
                x = current_row[feature_cols].values.reshape(1, -1)
                predicted = float(model_obj.predict(x)[0])
            except Exception:
                predicted = float(current_row["close"])

        points.append(
            {
                "date": pd.to_datetime(next_row["timestamp"]).strftime("%Y-%m-%d"),
                "actual": actual,
                "predicted": predicted,
                "abs_error": abs(actual - predicted),
            }
        )

    if not points:
        raise HTTPException(status_code=400, detail="No comparison points generated.")

    y_true = np.array([point["actual"] for point in points], dtype=float)
    y_pred = np.array([point["predicted"] for point in points], dtype=float)

    return {
        "symbol": symbol,
        "model": model_used,
        "count": len(points),
        "metrics": {
            "mae": float(mean_absolute_error(y_true, y_pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        },
        "points": points,
    }


@router.get("/user/backtest")
def user_backtest(
    symbol: str = "BTC-USD",
    model: str = "random_forest",
    initial_capital: float = 10000.0,
    test_size: float = 0.2,
    current_user: sqlite3.Row = Depends(require_role("user", "researcher", "admin")),
):
    symbol = normalize_symbol(symbol)
    model = model.strip().lower()
    initial_capital = max(100.0, min(float(initial_capital), 10_000_000.0))
    test_size = max(0.05, min(float(test_size), 0.5))

    raw_df = get_symbol_dataframe(symbol)
    feature_df = build_features(raw_df)
    if len(feature_df) < 60:
        raise HTTPException(status_code=400, detail="Not enough historical data for backtesting.")

    feature_cols = ["open", "high", "low", "close", "volume", "ma_fast", "ma_slow", "rsi", "macd", "volatility"]

    conn = get_connection()
    deployed = None
    try:
        deployed = conn.execute(
            """
            SELECT model_name, artifact_path FROM experiments
            WHERE symbol = ? AND is_deployed = 1 AND model_name = ?
            ORDER BY datetime(created_at) DESC LIMIT 1
            """,
            (symbol, model),
        ).fetchone()
        if not deployed:
            deployed = conn.execute(
                """
                SELECT model_name, artifact_path FROM experiments
                WHERE symbol = ? AND is_deployed = 1
                ORDER BY datetime(created_at) DESC LIMIT 1
                """,
                (symbol,),
            ).fetchone()
    finally:
        conn.close()

    model_obj = None
    model_used = "naive_baseline"
    if deployed:
        try:
            artifact = joblib.load(deployed["artifact_path"])
            model_obj = artifact.get("model")
            loaded_cols = artifact.get("feature_cols")
            if model_obj is not None and loaded_cols:
                feature_cols = loaded_cols
                model_used = deployed["model_name"]
        except Exception:
            model_obj = None

    if model_obj is None:
        feature_df_with_target = feature_df.copy()
        feature_df_with_target["target"] = feature_df_with_target["close"].shift(-1)
        feature_df_with_target = feature_df_with_target.dropna().reset_index(drop=True)

        split = int(len(feature_df_with_target) * (1 - test_size))
        X_train = feature_df_with_target.iloc[:split][feature_cols].values
        y_train = feature_df_with_target.iloc[:split]["target"].values
        model_obj = RandomForestRegressor(n_estimators=100, random_state=42)
        model_obj.fit(X_train, y_train)
        model_used = "random_forest_inline"

    test_start = int(len(feature_df) * (1 - test_size))
    test_df = feature_df.iloc[test_start:].reset_index(drop=True)
    if len(test_df) < 5:
        raise HTTPException(status_code=400, detail="Test window too small.")

    cash = initial_capital
    shares = 0.0

    equity_curve: List[Dict[str, Any]] = []
    trades: List[Dict[str, Any]] = []

    for index in range(len(test_df) - 1):
        row = test_df.iloc[index]
        next_row = test_df.iloc[index + 1]
        price_now = float(row["close"])
        price_next = float(next_row["close"])

        try:
            x = row[feature_cols].values.reshape(1, -1)
            predicted_next = float(model_obj.predict(x)[0])
        except Exception:
            predicted_next = price_now

        signal = "buy" if predicted_next > price_now else "sell"

        if signal == "buy" and cash > 0 and price_next > 0:
            shares_bought = cash / price_next
            shares += shares_bought
            cost = shares_bought * price_next
            cash -= cost
            trades.append(
                {
                    "date": pd.to_datetime(next_row["timestamp"]).strftime("%Y-%m-%d"),
                    "action": "buy",
                    "price": round(price_next, 2),
                    "shares": round(shares_bought, 6),
                    "value": round(cost, 2),
                }
            )
        elif signal == "sell" and shares > 0 and price_next > 0:
            proceeds = shares * price_next
            cash += proceeds
            trades.append(
                {
                    "date": pd.to_datetime(next_row["timestamp"]).strftime("%Y-%m-%d"),
                    "action": "sell",
                    "price": round(price_next, 2),
                    "shares": round(shares, 6),
                    "value": round(proceeds, 2),
                }
            )
            shares = 0.0

        portfolio_value = cash + shares * price_next
        equity_curve.append(
            {
                "date": pd.to_datetime(next_row["timestamp"]).strftime("%Y-%m-%d"),
                "portfolio_value": round(portfolio_value, 2),
                "price": round(price_next, 2),
                "signal": signal,
            }
        )

    bah_entry = float(test_df.iloc[0]["close"])
    bah_exit = float(test_df.iloc[-1]["close"])
    bah_shares = initial_capital / bah_entry if bah_entry > 0 else 0
    bah_final = bah_shares * bah_exit
    bah_return_pct = ((bah_final - initial_capital) / initial_capital) * 100

    final_value = cash + shares * float(test_df.iloc[-1]["close"])
    total_return_pct = ((final_value - initial_capital) / initial_capital) * 100

    pv_series = np.array([point["portfolio_value"] for point in equity_curve], dtype=float)
    if len(pv_series) > 1:
        daily_returns = np.diff(pv_series) / np.where(pv_series[:-1] > 0, pv_series[:-1], 1)
        sharpe = float((np.mean(daily_returns) / (np.std(daily_returns) + 1e-9)) * math.sqrt(252))
    else:
        sharpe = 0.0

    peak = pv_series[0] if len(pv_series) else initial_capital
    max_dd = 0.0
    for value in pv_series:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak if peak > 0 else 0.0
        if drawdown > max_dd:
            max_dd = drawdown

    buys = [trade for trade in trades if trade["action"] == "buy"]
    sells = [trade for trade in trades if trade["action"] == "sell"]
    wins = sum(
        1
        for sell in sells
        if sell["value"] > (buys[sells.index(sell)]["value"] if sells.index(sell) < len(buys) else 0)
    )
    win_rate = (wins / len(sells) * 100) if sells else 0.0

    bah_per_day = [
        {
            "date": point["date"],
            "bah_value": round(bah_shares * point["price"], 2),
        }
        for point in equity_curve
    ]

    return {
        "symbol": symbol,
        "model": model_used,
        "initial_capital": initial_capital,
        "final_value": round(final_value, 2),
        "total_return_pct": round(total_return_pct, 2),
        "bah_return_pct": round(bah_return_pct, 2),
        "bah_final_value": round(bah_final, 2),
        "sharpe_ratio": round(sharpe, 3),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "win_rate_pct": round(win_rate, 2),
        "total_trades": len(trades),
        "test_days": len(equity_curve),
        "equity_curve": equity_curve,
        "bah_curve": bah_per_day,
        "trades": trades[-50:],
    }


@router.post("/user/chat")
def user_chat(
    payload: ChatRequest,
    user: sqlite3.Row = Depends(require_role("user", "researcher", "admin")),
):
    system_prompt = (
        "You are a knowledgeable and friendly cryptocurrency assistant embedded in a crypto price "
        "prediction platform. You help users understand cryptocurrencies, blockchain technology, "
        "DeFi, trading concepts, market analysis, and the predictions made on this platform. "
        "Be concise, clear, and always include a short disclaimer that your responses are "
        "not financial advice when discussing prices or investment topics. "
        "Keep replies under 300 words unless the user explicitly asks for detail."
    )

    fallback_reply = (
        "I'm sorry, I'm unable to answer right now — the AI service is not configured. "
        "Please ensure a valid GEMINI_API_KEY is set in the environment."
    )

    api_key = get_gemini_api_key()
    if not api_key:
        return {"reply": fallback_reply, "provider": "none"}

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)

        conversation_parts: List[dict] = []
        for msg in payload.history[-20:]:
            role = "user" if msg.role == "user" else "model"
            conversation_parts.append({"role": role, "parts": [{"text": msg.content}]})

        conversation_parts.append({"role": "user", "parts": [{"text": payload.message}]})

        candidate_models = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-flash-latest",
            "gemini-pro-latest",
        ]

        for model_name in candidate_models:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_prompt,
                )
                response = model.generate_content(conversation_parts)
                text = (response.text or "").strip()
                if text:
                    return {"reply": text, "provider": "gemini"}
            except Exception:
                continue

    except Exception:
        pass

    return {"reply": fallback_reply, "provider": "none"}