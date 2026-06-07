import sqlite3
from typing import Optional

from api.repositories import users as user_repository


def track_activity(get_connection_fn, now_utc_fn, user_id: Optional[int], action: str, details: str = "") -> None:
    conn = get_connection_fn()
    try:
        conn.execute(
            "INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
            (user_id, action, details, now_utc_fn()),
        )
        conn.commit()
    finally:
        conn.close()


def track_api_usage(get_connection_fn, now_utc_fn, provider: str, endpoint: str, user_id: Optional[int]) -> None:
    conn = get_connection_fn()
    try:
        existing = conn.execute(
            "SELECT id, request_count FROM api_usage WHERE provider = ? AND endpoint = ?",
            (provider, endpoint),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE api_usage SET request_count = ?, last_called_at = ?, user_id = ? WHERE id = ?",
                (int(existing["request_count"]) + 1, now_utc_fn(), user_id, existing["id"]),
            )
        else:
            conn.execute(
                """
                INSERT INTO api_usage (provider, endpoint, user_id, request_count, last_called_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (provider, endpoint, user_id, now_utc_fn()),
            )
        conn.commit()
    finally:
        conn.close()


def get_user_by_email(get_connection_fn, email: str) -> Optional[sqlite3.Row]:
    conn = get_connection_fn()
    try:
        return user_repository.get_by_email(conn, email)
    finally:
        conn.close()
