import sqlite3
from typing import Callable, Optional

from fastapi import Depends, Header, HTTPException

from api.core import config as core_config
from api.core import database as core_database
from api.core import security as core_security


def get_current_user(
    authorization: Optional[str],
    parse_bearer_token_fn: Callable[[Optional[str]], str],
    hash_session_token_fn: Callable[[str], str],
    get_connection_fn: Callable[[], sqlite3.Connection],
) -> sqlite3.Row:
    raw_token = parse_bearer_token_fn(authorization)
    token_hash = hash_session_token_fn(raw_token)
    conn = get_connection_fn()
    try:
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


def require_role(get_current_user_fn: Callable, *roles: str):
    def dependency(user: sqlite3.Row = Depends(get_current_user_fn)) -> sqlite3.Row:
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions.")
        return user

    return dependency


def get_current_user_default(authorization: Optional[str] = Header(default=None)) -> sqlite3.Row:
    return get_current_user(
        authorization,
        core_security.parse_bearer_token,
        core_security.hash_session_token,
        lambda: core_database.get_connection(core_config.DB_PATH),
    )


def require_role_default(*roles: str):
    return require_role(get_current_user_default, *roles)
