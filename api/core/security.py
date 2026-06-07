import hashlib
import os
from typing import Optional

from fastapi import HTTPException
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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


def hash_password(password: str, context: CryptContext | None = None) -> str:
    return (context or pwd_context).hash(password)


def verify_password(password: str, stored_hash: str, context: CryptContext | None = None) -> bool:
    try:
        return (context or pwd_context).verify(password, stored_hash)
    except Exception:
        return False


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
