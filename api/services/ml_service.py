import math
from typing import Any, Callable, Dict, Optional

import numpy as np
import pandas as pd
from fastapi import HTTPException
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def build_features(df: pd.DataFrame, fast_window: int = 7, slow_window: int = 21) -> pd.DataFrame:
    data = df.copy()
    data["returns"] = data["close"].pct_change()
    data["ma_fast"] = data["close"].rolling(fast_window).mean()
    data["ma_slow"] = data["close"].rolling(slow_window).mean()
    delta = data["close"].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    rs = up.rolling(14).mean() / down.rolling(14).mean().replace(0, np.nan)
    data["rsi"] = 100 - (100 / (1 + rs))
    ema_12 = data["close"].ewm(span=12, adjust=False).mean()
    ema_26 = data["close"].ewm(span=26, adjust=False).mean()
    data["macd"] = ema_12 - ema_26
    data["volatility"] = data["returns"].rolling(14).std() * math.sqrt(14)
    data = data.dropna().reset_index(drop=True)
    return data


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    mape = np.mean(np.abs((y_true - y_pred) / np.clip(np.abs(y_true), 1e-6, None))) * 100
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mape": float(mape),
        "r2": float(r2_score(y_true, y_pred)),
    }


def get_symbol_dataframe(symbol: str, get_connection: Callable[[], Any]) -> pd.DataFrame:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT timestamp, open, high, low, close, volume
            FROM historical_prices
            WHERE symbol = ?
            ORDER BY datetime(timestamp) ASC
            """,
            (symbol,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        raise HTTPException(status_code=400, detail=f"No historical data found for {symbol}.")

    df = pd.DataFrame([dict(row) for row in rows])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def get_latest_price_and_change(
    symbol: str,
    get_connection: Callable[[], Any],
    yf_module: Any,
) -> tuple[Optional[float], Optional[float]]:
    live_price: Optional[float] = None
    live_prev: Optional[float] = None

    try:
        ticker = yf_module.Ticker(symbol)
        hist = ticker.history(period="2d", interval="1d")
        if hist is not None and len(hist) >= 1:
            closes = hist["Close"].dropna().tolist()
            if closes:
                live_price = float(closes[-1])
                if len(closes) >= 2:
                    live_prev = float(closes[-2])
    except Exception:
        pass

    if live_price is not None:
        pct = ((live_price - live_prev) / live_prev) * 100.0 if live_prev and live_prev > 0 else None
        return live_price, pct

    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT close
            FROM historical_prices
            WHERE symbol = ?
            ORDER BY datetime(timestamp) DESC
            LIMIT 2
            """,
            (symbol,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return None, None

    latest = float(rows[0]["close"])
    if len(rows) < 2 or rows[1]["close"] in (None, 0):
        return latest, None

    prev = float(rows[1]["close"])
    pct = ((latest - prev) / max(prev, 1e-6)) * 100.0
    return latest, float(pct)


def evaluate_alert_condition(
    alert: Dict[str, Any],
    latest_price: Optional[float] = None,
    pct_change_24h: Optional[float] = None,
    sentiment_label: Optional[str] = None,
) -> Dict[str, Any]:
    is_triggered = False
    reason = None

    if alert["alert_type"] == "target" and latest_price is not None and alert["threshold_value"] is not None:
        threshold = float(alert["threshold_value"])
        if alert["direction"] == "above":
            is_triggered = latest_price >= threshold
        else:
            is_triggered = latest_price <= threshold
        if is_triggered:
            reason = f"Price {latest_price:.2f} crossed {alert['direction']} target {threshold:.2f}."

    elif alert["alert_type"] == "percent" and pct_change_24h is not None and alert["threshold_value"] is not None:
        threshold = float(alert["threshold_value"])
        if alert["direction"] == "above":
            is_triggered = pct_change_24h >= threshold
        else:
            is_triggered = pct_change_24h <= -abs(threshold)
        if is_triggered:
            reason = (
                f"24h change {pct_change_24h:.2f}% triggered {alert['direction']} threshold {threshold:.2f}%."
            )

    elif alert["alert_type"] == "sentiment" and sentiment_label:
        expected = (alert.get("sentiment_label") or "").strip().lower()
        normalized_sentiment = sentiment_label.strip().lower()
        is_triggered = normalized_sentiment == expected
        if is_triggered:
            reason = f"Sentiment is {normalized_sentiment}, matching alert."

    return {
        "latest_price": latest_price,
        "pct_change_24h": pct_change_24h,
        "is_triggered": is_triggered,
        "reason": reason,
    }


def compute_risk_profile(raw_df: pd.DataFrame) -> tuple[float, str]:
    closes = pd.to_numeric(raw_df.get("close"), errors="coerce").dropna()
    returns = closes.pct_change().dropna().tail(30)
    if returns.empty:
        return 50.0, "medium"

    vol_pct = float(returns.std() * math.sqrt(30) * 100)
    score = float(np.clip(vol_pct * 2.5, 1.0, 100.0))

    if score < 33:
        level = "low"
    elif score < 66:
        level = "medium"
    else:
        level = "high"
    return score, level


def build_risk_note(risk_level: str, risk_tolerance: str) -> str:
    if risk_level == "high" and risk_tolerance == "low":
        return "Current market volatility is high versus your low risk preference. Consider reducing position size."
    if risk_level == "low" and risk_tolerance == "high":
        return "Market volatility is currently low compared to your high risk preference."
    if risk_level == "medium":
        return "Market volatility is in a moderate range. Manage position sizing and stop-loss levels carefully."
    return f"Market volatility is currently {risk_level}."


def generate_explanation(
    symbol: str,
    horizon: int,
    predicted_price: float,
    trend: str,
    confidence: float,
    mode: str,
    last_close: float,
    get_gemini_api_key: Callable[[], Optional[str]],
) -> tuple[str, str]:
    direction = "increase" if trend == "bullish" else "decrease"
    fallback = (
        f"Technical view for {symbol}: the deployed model projects a {direction} over {horizon} day(s). "
        f"Predicted price is {predicted_price:.2f} vs latest close {last_close:.2f}. "
        f"Confidence proxy is {confidence:.2f}%, based on recent residual dispersion and trend stability. "
        "Interpret this with volatility and liquidity context before taking a position."
        if mode == "technical"
        else (
            f"For {symbol}, the model expects the price to {direction} in about {horizon} day(s). "
            f"Estimated price: {predicted_price:.2f}. Confidence: {confidence:.2f}%. "
            "This is an estimate, not financial advice."
        )
    )

    api_key = get_gemini_api_key()
    if not api_key:
        return fallback, "local_explainer"

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        prompt = (
            f"You are a crypto assistant. Provide a {mode} explanation for a price prediction. "
            f"Symbol: {symbol}, horizon: {horizon} day(s), trend: {trend}, "
            f"predicted price: {predicted_price:.2f}, last close: {last_close:.2f}, "
            f"confidence: {confidence:.2f}%. Keep it concise and responsible."
        )
        candidate_models = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-flash-latest",
            "gemini-pro-latest",
        ]

        for model_name in candidate_models:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                text = (response.text or "").strip()
                if text:
                    return text, "gemini"
            except Exception:
                continue
    except Exception:
        pass

    return fallback, "local_explainer"
