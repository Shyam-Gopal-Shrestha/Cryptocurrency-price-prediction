import hashlib
import os
import secrets
import sqlite3
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


DB_PATH = os.path.join(os.path.dirname(__file__), "auth.db")
ALLOWED_ROLES = {"user", "researcher", "admin"}

router = APIRouter(tags=["auth"])


class SignupRequest(BaseModel):
    email: str
    password: str
    role: str = "user"


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)


def get_connection() -> sqlite3.Connection:
    # Create a sqlite connection with row access by column name.
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_email(email: str) -> str:
    # Normalize and minimally validate email shape without extra dependencies.
    normalized = email.strip().lower()
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise HTTPException(status_code=400, detail="Invalid email format.")
    return normalized


def init_auth_db() -> None:
    # Ensure the users table exists before serving auth requests.
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def hash_password(password: str) -> str:
    # Hash password with random salt and return in "salt$hash" format.
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    # Verify an incoming password against stored "salt$hash".
    try:
        salt, saved_digest = stored_hash.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()
    return secrets.compare_digest(digest, saved_digest)


def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    # Fetch one user record by email, or None when not found.
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, email, password_hash, role FROM users WHERE email = ?",
            (email.lower(),),
        ).fetchone()
        return row
    finally:
        conn.close()


@router.post("/signup")
def signup(payload: SignupRequest):
    # Create a user after validating role and ensuring unique email.
    role = payload.role.strip().lower()
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role.")

    email = normalize_email(payload.email)
    if len(payload.password.strip()) < 6:
        raise HTTPException(
            status_code=400, detail="Password must be at least 6 characters."
        )
    if get_user_by_email(email):
        raise HTTPException(status_code=409, detail="Email already registered.")

    password_hash = hash_password(payload.password)
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)",
            (email, password_hash, role),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "message": "User created successfully",
        "user": {"id": cursor.lastrowid, "email": email, "role": role},
    }


@router.post("/login")
def login(payload: LoginRequest):
    # Authenticate by email/password and return user profile for frontend session.
    email = normalize_email(payload.email)
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    return {"id": user["id"], "email": user["email"], "role": user["role"]}


init_auth_db()
