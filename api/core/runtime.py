import sqlite3
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import yfinance as yf
from fastapi import HTTPException, Header

from api.core import config as core_config
from api.core import database as core_database
from api.core import dependencies as core_dependencies
from api.core import security as core_security
from api.services import alert_service, auth_service, explanation_service, ml_service

DB_PATH = core_config.DB_PATH
ALLOWED_ROLES = core_config.ALLOWED_ROLES
ALLOWED_REQUEST_ROLES = core_config.ALLOWED_REQUEST_ROLES
SESSION_HOURS = core_config.SESSION_HOURS
MODEL_STORAGE_DIR = core_config.MODEL_STORAGE_DIR
BASE_DIR = core_config.BASE_DIR
HAS_XGBOOST = core_config.HAS_XGBOOST
pwd_context = core_security.pwd_context


def get_connection() -> sqlite3.Connection:
    return core_database.get_connection(DB_PATH)


def now_utc() -> str:
    return core_database.now_utc()


def normalize_email(email: str) -> str:
    return core_security.normalize_email(email)


def normalize_symbol(symbol: str) -> str:
    return core_security.normalize_symbol(symbol)


def parse_bearer_token(authorization: Optional[str]) -> str:
    return core_security.parse_bearer_token(authorization)


def hash_password(password: str) -> str:
    return core_security.hash_password(password, pwd_context)


def verify_password(password: str, stored_hash: str) -> bool:
    return core_security.verify_password(password, stored_hash, pwd_context)


def track_activity(user_id: Optional[int], action: str, details: str = "") -> None:
    auth_service.track_activity(get_connection, now_utc, user_id, action, details)


def track_api_usage(provider: str, endpoint: str, user_id: Optional[int]) -> None:
    auth_service.track_api_usage(get_connection, now_utc, provider, endpoint, user_id)


def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    return auth_service.get_user_by_email(get_connection, email)


def hash_session_token(token: str) -> str:
    return core_security.hash_session_token(token)


def get_gemini_api_key() -> Optional[str]:
    return core_security.get_gemini_api_key()


def get_current_user(authorization: Optional[str] = Header(default=None)) -> sqlite3.Row:
    return core_dependencies.get_current_user(
        authorization,
        parse_bearer_token,
        hash_session_token,
        get_connection,
    )


def require_role(*roles: str):
    return core_dependencies.require_role(get_current_user, *roles)


def table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return core_database.table_columns(conn, table_name)


def ensure_users_schema(conn: sqlite3.Connection) -> None:
    core_database.ensure_users_schema(conn)


def ensure_alerts_schema(conn: sqlite3.Connection) -> None:
    core_database.ensure_alerts_schema(conn)


def init_auth_db() -> None:
    core_database.init_auth_db(get_connection, now_utc, MODEL_STORAGE_DIR, normalize_email, hash_password)


def bootstrap_admin() -> None:
    core_database.bootstrap_admin(get_connection, normalize_email, hash_password, now_utc)


def build_features(df: pd.DataFrame, fast_window: int = 7, slow_window: int = 21) -> pd.DataFrame:
    return ml_service.build_features(df, fast_window, slow_window)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    return ml_service.compute_metrics(y_true, y_pred)


def get_symbol_dataframe(symbol: str) -> pd.DataFrame:
    return ml_service.get_symbol_dataframe(symbol, get_connection)


def get_latest_price_and_change(symbol: str) -> tuple[Optional[float], Optional[float]]:
    return ml_service.get_latest_price_and_change(symbol, get_connection, yf)


def evaluate_alert_condition(
    alert: Dict[str, Any],
    latest_price: Optional[float] = None,
    pct_change_24h: Optional[float] = None,
    sentiment_label: Optional[str] = None,
) -> Dict[str, Any]:
    return alert_service.evaluate_alert_condition(alert, latest_price, pct_change_24h, sentiment_label)


def compute_risk_profile(raw_df: pd.DataFrame) -> tuple[float, str]:
    return ml_service.compute_risk_profile(raw_df)


def build_risk_note(risk_level: str, risk_tolerance: str) -> str:
    return ml_service.build_risk_note(risk_level, risk_tolerance)


def generate_explanation(
    symbol: str,
    horizon: int,
    predicted_price: float,
    trend: str,
    confidence: float,
    mode: str,
    last_close: float,
) -> tuple[str, str]:
    return explanation_service.generate_explanation(
        symbol,
        horizon,
        predicted_price,
        trend,
        confidence,
        mode,
        last_close,
        get_gemini_api_key,
    )


init_auth_db()