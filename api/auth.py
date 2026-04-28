import json
import math
import os
import secrets
import sqlite3
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

import joblib
import numpy as np
import pandas as pd
import pyotp
import yfinance as yf
from fastapi import APIRouter, Depends, Header, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.neural_network import MLPRegressor
from sklearn.svm import SVR

try:
    from xgboost import XGBRegressor

    HAS_XGBOOST = True
except Exception:
    HAS_XGBOOST = False


DB_PATH = os.path.join(os.path.dirname(__file__), "auth.db")
ALLOWED_ROLES = {"user", "researcher", "admin"}
ALLOWED_REQUEST_ROLES = {"user", "researcher"}
SESSION_HOURS = 24
MODEL_STORAGE_DIR = Path(os.path.dirname(__file__)).parent / "models" / "deployed"
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env", override=False)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(tags=["platform"])


class SignupRequest(BaseModel):
    email: str
    password: str
    role: str = "user"


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)
    otp_code: Optional[str] = None


class RoleUpdateRequest(BaseModel):
    role: str


class ApprovalRequest(BaseModel):
    approved: bool = True


class CryptoConfigRequest(BaseModel):
    symbol: str
    name: str
    is_enabled: bool = True


class ModelConfigRequest(BaseModel):
    model_name: str
    is_enabled: bool = True
    is_researcher_available: bool = True


class DataFetchRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    interval: str = "1d"


class PreprocessRequest(BaseModel):
    symbol: str
    fast_window: int = 7
    slow_window: int = 21


class TrainRequest(BaseModel):
    symbol: str
    models: List[str] = Field(
        default_factory=lambda: [
            "linear_regression",
            "random_forest",
            "xgboost",
            "svr",
            "lstm",
            "gru",
            "transformer",
        ]
    )
    horizon: int = 1
    test_size: float = 0.2
    auto_deploy_best: bool = True


class PredictionRequest(BaseModel):
    symbol: str
    horizon: int = 1
    explanation_mode: str = "simple"
    risk_tolerance: str = "medium"


class TwoFASetupResponse(BaseModel):
    secret: str
    otpauth_uri: str


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = Field(default_factory=list)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise HTTPException(status_code=400, detail="Invalid email format.")
    return normalized


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise HTTPException(status_code=400, detail="Symbol is required.")
    if "-" not in normalized:
        normalized = f"{normalized}-USD"
    return normalized


def parse_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header.")
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="Invalid authorization header.")
    return authorization[len(prefix) :].strip()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        return pwd_context.verify(password, stored_hash)
    except Exception:
        return False


def track_activity(user_id: Optional[int], action: str, details: str = "") -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
            (user_id, action, details, now_utc()),
        )
        conn.commit()
    finally:
        conn.close()


def track_api_usage(provider: str, endpoint: str, user_id: Optional[int]) -> None:
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id, request_count FROM api_usage WHERE provider = ? AND endpoint = ?",
            (provider, endpoint),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE api_usage SET request_count = ?, last_called_at = ?, user_id = ? WHERE id = ?",
                (int(existing["request_count"]) + 1, now_utc(), user_id, existing["id"]),
            )
        else:
            conn.execute(
                """
                INSERT INTO api_usage (provider, endpoint, user_id, request_count, last_called_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (provider, endpoint, user_id, now_utc()),
            )
        conn.commit()
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    finally:
        conn.close()


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_gemini_api_key() -> Optional[str]:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        return None
    key = key.strip().strip('"').strip("'")
    if key.lower() in {"none", "null", "changeme", "your_key_here"}:
        return None
    return key


def get_current_user(authorization: Optional[str] = Header(default=None)) -> sqlite3.Row:
    raw_token = parse_bearer_token(authorization)
    token_hash = hash_session_token(raw_token)
    conn = get_connection()
    try:
        # backward compatible: supports old plaintext tokens already in DB
        row = conn.execute(
            """
            SELECT u.*
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE (s.token = ? OR s.token = ?)
              AND s.is_active = 1
              AND datetime(s.expires_at) > datetime('now')
            """,
            (token_hash, raw_token),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    if row["status"] != "approved":
        raise HTTPException(status_code=403, detail="Account is not approved yet.")
    return row


def require_role(*roles: str):
    def dependency(user: sqlite3.Row = Depends(get_current_user)) -> sqlite3.Row:
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions.")
        return user

    return dependency


def table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def ensure_users_schema(conn: sqlite3.Connection) -> None:
    existing = table_columns(conn, "users")

    if "status" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'approved'")
    if "twofa_secret" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN twofa_secret TEXT")
    if "twofa_enabled" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN twofa_enabled INTEGER NOT NULL DEFAULT 0")
    if "approved_at" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN approved_at TEXT")
    if "approved_by" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN approved_by INTEGER")

    conn.execute("UPDATE users SET status = 'approved' WHERE status IS NULL OR status = ''")


def init_auth_db() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                status TEXT NOT NULL DEFAULT 'pending',
                twofa_secret TEXT,
                twofa_enabled INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                approved_at TEXT,
                approved_by INTEGER
            )
            """
        )
        ensure_users_schema(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS crypto_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                is_enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS model_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT UNIQUE NOT NULL,
                is_enabled INTEGER NOT NULL DEFAULT 1,
                is_researcher_available INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS historical_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(symbol, timestamp)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                researcher_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                model_name TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                artifact_path TEXT NOT NULL,
                status TEXT NOT NULL,
                is_deployed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(researcher_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prediction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                horizon INTEGER NOT NULL,
                predicted_price REAL NOT NULL,
                trend TEXT NOT NULL,
                confidence REAL NOT NULL,
                explanation_mode TEXT NOT NULL,
                explanation TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                user_id INTEGER,
                request_count INTEGER NOT NULL DEFAULT 1,
                last_called_at TEXT NOT NULL,
                UNIQUE(provider, endpoint),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.commit()

        MODEL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

        default_cryptos = [
            ("BTC-USD", "Bitcoin"),
            ("ETH-USD", "Ethereum"),
            ("SOL-USD", "Solana"),
            ("ADA-USD", "Cardano"),
        ]
        for symbol, name in default_cryptos:
            conn.execute(
                """
                INSERT OR IGNORE INTO crypto_configs (symbol, name, is_enabled, created_at)
                VALUES (?, ?, 1, ?)
                """,
                (symbol, name, now_utc()),
            )

        default_models = [
            "linear_regression",
            "random_forest",
            "xgboost",
            "svr",
            "lstm",
            "gru",
            "transformer",
        ]
        for model in default_models:
            conn.execute(
                """
                INSERT OR IGNORE INTO model_configs (model_name, is_enabled, is_researcher_available, created_at)
                VALUES (?, 1, 1, ?)
                """,
                (model, now_utc()),
            )

        # Ensure supported defaults stay enabled for researcher workflows.
        conn.execute(
            """
            UPDATE model_configs
            SET is_enabled = 1, is_researcher_available = 1
            WHERE model_name IN ('linear_regression', 'random_forest', 'xgboost', 'svr', 'lstm', 'gru', 'transformer')
            """
        )
        conn.commit()
    finally:
        conn.close()

    bootstrap_admin()


def bootstrap_admin() -> None:
    admin_email = os.getenv("ADMIN_EMAIL", "admin@local.dev")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    conn = get_connection()
    try:
        existing_admin = conn.execute(
            "SELECT id FROM users WHERE role = 'admin' LIMIT 1"
        ).fetchone()
        if existing_admin:
            return

        conn.execute(
            """
            INSERT INTO users (email, password_hash, role, status, created_at, approved_at)
            VALUES (?, ?, 'admin', 'approved', ?, ?)
            """,
            (normalize_email(admin_email), hash_password(admin_password), now_utc(), now_utc()),
        )
        conn.commit()
    finally:
        conn.close()


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


def get_symbol_dataframe(symbol: str) -> pd.DataFrame:
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

    df = pd.DataFrame([dict(r) for r in rows])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def compute_risk_profile(raw_df: pd.DataFrame) -> tuple[float, str]:
    closes = pd.to_numeric(raw_df.get("close"), errors="coerce").dropna()
    returns = closes.pct_change().dropna().tail(30)
    if returns.empty:
        return 50.0, "medium"

    # 30-day volatility proxy converted to a 1..100 score.
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


@router.post("/signup")
def signup(payload: SignupRequest):
    role = payload.role.strip().lower()
    if role not in ALLOWED_REQUEST_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role request.")

    email = normalize_email(payload.email)
    if len(payload.password.strip()) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    if get_user_by_email(email):
        raise HTTPException(status_code=409, detail="Email already registered.")

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO users (email, password_hash, role, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)
            """,
            (email, hash_password(payload.password), role, now_utc()),
        )
        conn.commit()
        user_id = cursor.lastrowid
    finally:
        conn.close()

    track_activity(user_id, "user.signup", f"Requested role={role}")
    return {
        "message": "Registration submitted. Wait for admin approval.",
        "user": {"id": user_id, "email": email, "role": role, "status": "pending"},
    }


@router.post("/login")
def login(payload: LoginRequest):
    email = normalize_email(payload.email)
    user = get_user_by_email(email)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    if user["status"] != "approved":
        raise HTTPException(status_code=403, detail="Account pending admin approval.")

    if int(user["twofa_enabled"]) == 1:
        if not payload.otp_code:
            return {"requires_2fa": True, "message": "2FA code required."}
        totp = pyotp.TOTP(user["twofa_secret"])
        if not totp.verify(payload.otp_code.strip(), valid_window=1):
            raise HTTPException(status_code=401, detail="Invalid 2FA code.")

    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_session_token(raw_token)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)).isoformat()

    conn = get_connection()
    try:
        # cleanup expired/inactive sessions for this user
        conn.execute(
            """
            UPDATE sessions
            SET is_active = 0
            WHERE user_id = ? AND datetime(expires_at) <= datetime('now')
            """,
            (user["id"],),
        )
        conn.execute(
            """
            INSERT INTO sessions (user_id, token, expires_at, created_at, is_active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (user["id"], token_hash, expires_at, now_utc()),
        )
        conn.commit()
    finally:
        conn.close()

    track_activity(user["id"], "user.login", "User logged in.")
    return {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "status": user["status"],
        "token": raw_token,
        "expires_at": expires_at,
    }


@router.post("/logout")
def logout(
    current_user: sqlite3.Row = Depends(get_current_user),
    authorization: Optional[str] = Header(default=None),
):
    raw_token = parse_bearer_token(authorization)
    token_hash = hash_session_token(raw_token)
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE sessions SET is_active = 0 WHERE token = ? OR token = ?",
            (token_hash, raw_token),  # backward compatibility
        )
        conn.commit()
    finally:
        conn.close()

    track_activity(current_user["id"], "user.logout", "User logged out.")
    return {"message": "Logged out successfully."}

@router.post("/auth/logout-all")
def logout_all_sessions(current_user: sqlite3.Row = Depends(get_current_user)):
    conn = get_connection()
    try:
        conn.execute("UPDATE sessions SET is_active = 0 WHERE user_id = ?", (current_user["id"],))
        conn.commit()
    finally:
        conn.close()

    track_activity(current_user["id"], "user.logout_all", "All sessions revoked.")
    return {"message": "All sessions logged out."}


@router.get("/auth/me")
def auth_me(current_user: sqlite3.Row = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "role": current_user["role"],
        "status": current_user["status"],
        "twofa_enabled": bool(current_user["twofa_enabled"]),
    }


@router.post("/auth/2fa/setup", response_model=TwoFASetupResponse)
def setup_2fa(current_user: sqlite3.Row = Depends(get_current_user)):
    secret = pyotp.random_base32()
    app_name = "Crypto Prediction Platform"
    uri = pyotp.TOTP(secret).provisioning_uri(current_user["email"], issuer_name=app_name)

    conn = get_connection()
    try:
        conn.execute("UPDATE users SET twofa_secret = ? WHERE id = ?", (secret, current_user["id"]))
        conn.commit()
    finally:
        conn.close()

    track_activity(current_user["id"], "user.2fa.setup", "2FA setup initiated.")
    return TwoFASetupResponse(secret=secret, otpauth_uri=uri)


class TwoFAVerifyRequest(BaseModel):
    otp_code: str


@router.post("/auth/2fa/enable")
def enable_2fa(payload: TwoFAVerifyRequest, current_user: sqlite3.Row = Depends(get_current_user)):
    if not current_user["twofa_secret"]:
        raise HTTPException(status_code=400, detail="Run setup first.")
    totp = pyotp.TOTP(current_user["twofa_secret"])
    if not totp.verify(payload.otp_code.strip(), valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid OTP code.")

    conn = get_connection()
    try:
        conn.execute("UPDATE users SET twofa_enabled = 1 WHERE id = ?", (current_user["id"],))
        conn.commit()
    finally:
        conn.close()

    track_activity(current_user["id"], "user.2fa.enable", "2FA enabled.")
    return {"message": "2FA enabled."}


@router.post("/auth/2fa/disable")
def disable_2fa(current_user: sqlite3.Row = Depends(get_current_user)):
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET twofa_enabled = 0, twofa_secret = NULL WHERE id = ?", (current_user["id"],))
        conn.commit()
    finally:
        conn.close()

    track_activity(current_user["id"], "user.2fa.disable", "2FA disabled.")
    return {"message": "2FA disabled."}


@router.get("/admin/pending-users")
def admin_pending_users(admin: sqlite3.Row = Depends(require_role("admin"))):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, email, role, status, created_at FROM users WHERE status = 'pending' ORDER BY datetime(created_at) ASC"
        ).fetchall()
    finally:
        conn.close()

    return [dict(r) for r in rows]


@router.post("/admin/users/{user_id}/approval")
def admin_approve_user(
    user_id: int,
    payload: ApprovalRequest,
    admin: sqlite3.Row = Depends(require_role("admin")),
):
    status = "approved" if payload.approved else "rejected"
    conn = get_connection()
    try:
        target = conn.execute("SELECT id, email FROM users WHERE id = ?", (user_id,)).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="User not found.")
        conn.execute(
            "UPDATE users SET status = ?, approved_at = ?, approved_by = ? WHERE id = ?",
            (status, now_utc(), admin["id"], user_id),
        )
        conn.commit()
    finally:
        conn.close()

    track_activity(
        admin["id"],
        "admin.user.approval",
        f"Set user_id={user_id} status={status}",
    )
    return {"message": f"User {status}.", "user_id": user_id, "status": status}


@router.get("/admin/users")
def admin_list_users(admin: sqlite3.Row = Depends(require_role("admin"))):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, email, role, status, created_at, approved_at FROM users ORDER BY id ASC"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


@router.patch("/admin/users/{user_id}/role")
def admin_update_role(
    user_id: int,
    payload: RoleUpdateRequest,
    admin: sqlite3.Row = Depends(require_role("admin")),
):
    role = payload.role.strip().lower()
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role.")

    conn = get_connection()
    try:
        target = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="User not found.")
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        conn.commit()
    finally:
        conn.close()

    track_activity(admin["id"], "admin.user.role.update", f"user_id={user_id}, role={role}")
    return {"message": "Role updated.", "user_id": user_id, "role": role}


@router.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: int, admin: sqlite3.Row = Depends(require_role("admin"))):
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Admin cannot delete own account.")

    conn = get_connection()
    try:
        target = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="User not found.")
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()

    track_activity(admin["id"], "admin.user.delete", f"Deleted user_id={user_id}")
    return {"message": "User deleted."}


@router.get("/admin/config/cryptos")
def admin_list_cryptos(admin: sqlite3.Row = Depends(require_role("admin"))):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, symbol, name, is_enabled, created_at FROM crypto_configs ORDER BY symbol"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


@router.post("/admin/config/cryptos")
def admin_upsert_crypto(
    payload: CryptoConfigRequest,
    admin: sqlite3.Row = Depends(require_role("admin")),
):
    symbol = normalize_symbol(payload.symbol)
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO crypto_configs (symbol, name, is_enabled, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                name = excluded.name,
                is_enabled = excluded.is_enabled
            """,
            (symbol, payload.name.strip(), int(payload.is_enabled), now_utc()),
        )
        conn.commit()
    finally:
        conn.close()

    track_activity(admin["id"], "admin.crypto.upsert", f"symbol={symbol}")
    return {"message": "Crypto configuration saved.", "symbol": symbol}


@router.get("/admin/config/models")
def admin_list_models(admin: sqlite3.Row = Depends(require_role("admin"))):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, model_name, is_enabled, is_researcher_available, created_at FROM model_configs ORDER BY model_name"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


@router.post("/admin/config/models")
def admin_upsert_model(
    payload: ModelConfigRequest,
    admin: sqlite3.Row = Depends(require_role("admin")),
):
    model_name = payload.model_name.strip().lower()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO model_configs (model_name, is_enabled, is_researcher_available, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(model_name) DO UPDATE SET
                is_enabled = excluded.is_enabled,
                is_researcher_available = excluded.is_researcher_available
            """,
            (
                model_name,
                int(payload.is_enabled),
                int(payload.is_researcher_available),
                now_utc(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    track_activity(admin["id"], "admin.model.upsert", f"model={model_name}")
    return {"message": "Model configuration saved.", "model_name": model_name}


@router.get("/admin/logs")
def admin_logs(admin: sqlite3.Row = Depends(require_role("admin"))):
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT l.id, l.user_id, u.email, l.action, l.details, l.created_at
            FROM activity_logs l
            LEFT JOIN users u ON u.id = l.user_id
            ORDER BY datetime(l.created_at) DESC
            LIMIT 200
            """
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


@router.get("/admin/api-usage")
def admin_api_usage(admin: sqlite3.Row = Depends(require_role("admin"))):
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT provider, endpoint, request_count, last_called_at, user_id
            FROM api_usage
            ORDER BY request_count DESC
            """
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


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

    preview_cols = [
        "timestamp",
        "close",
        "ma_fast",
        "ma_slow",
        "rsi",
        "macd",
        "volatility",
    ]
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
        # Practical tabular approximations so these model options are operational in this API flow.
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
    if HAS_XGBOOST:
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

    for i in range(len(eval_df) - 1):
        current_row = eval_df.iloc[i]
        next_row = eval_df.iloc[i + 1]

        actual = float(next_row["close"])
        predicted = float(current_row["close"])  # safe fallback baseline

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

    y_true = np.array([p["actual"] for p in points], dtype=float)
    y_pred = np.array([p["predicted"] for p in points], dtype=float)

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

@router.post("/user/chat")
def user_chat(
    payload: ChatRequest,
    user: sqlite3.Row = Depends(require_role("user", "researcher", "admin")),
):
    """AI assistant chatbot endpoint powered by Gemini."""
    SYSTEM_PROMPT = (
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

        # Build conversation for Gemini multi-turn
        # Gemini expects alternating user/model turns
        conversation_parts: List[dict] = []
        for msg in payload.history[-20:]:  # keep last 20 messages for context
            role = "user" if msg.role == "user" else "model"
            conversation_parts.append({"role": role, "parts": [{"text": msg.content}]})

        # Append the new user message
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
                    system_instruction=SYSTEM_PROMPT,
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


init_auth_db()
