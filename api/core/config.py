import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
API_DIR = Path(__file__).resolve().parents[1]
DB_PATH = str(API_DIR / "auth.db")
ALLOWED_ROLES = {"user", "researcher", "admin"}
ALLOWED_REQUEST_ROLES = {"user", "researcher"}
SESSION_HOURS = 24
MODEL_STORAGE_DIR = BASE_DIR / "models" / "deployed"

load_dotenv(BASE_DIR / ".env", override=False)

try:
    from xgboost import XGBRegressor  # noqa: F401

    HAS_XGBOOST = True
except Exception:  # pragma: no cover
    HAS_XGBOOST = False  # pragma: no cover
