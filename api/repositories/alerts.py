import sqlite3
from typing import Any


def list_by_user(conn: sqlite3.Connection, user_id: int):
    return conn.execute(
        """
        SELECT id, symbol, alert_type, threshold_value, direction, sentiment_label, is_enabled,
               email_enabled, last_notified_at, created_at
        FROM alerts
        WHERE user_id = ?
        ORDER BY datetime(created_at) DESC
        """,
        (user_id,),
    ).fetchall()


def list_enabled_by_user(conn: sqlite3.Connection, user_id: int):
    return conn.execute(
        """
        SELECT id, symbol, alert_type, threshold_value, direction, sentiment_label, is_enabled,
               email_enabled, last_notified_at, created_at
        FROM alerts
        WHERE user_id = ? AND is_enabled = 1
        ORDER BY datetime(created_at) DESC
        """,
        (user_id,),
    ).fetchall()


def create(conn: sqlite3.Connection, values: tuple[Any, ...]):
    return conn.execute(
        """
        INSERT INTO alerts (
            user_id, symbol, alert_type, threshold_value, direction, sentiment_label,
            is_enabled, email_enabled, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        values,
    )


def find_for_user(conn: sqlite3.Connection, alert_id: int, user_id: int):
    return conn.execute("SELECT id FROM alerts WHERE id = ? AND user_id = ?", (alert_id, user_id)).fetchone()


def update_flags(conn: sqlite3.Connection, set_clause: str, params: tuple[Any, ...]) -> None:
    conn.execute(f"UPDATE alerts SET {set_clause} WHERE id = ? AND user_id = ?", params)


def delete_for_user(conn: sqlite3.Connection, alert_id: int, user_id: int) -> None:
    conn.execute("DELETE FROM alerts WHERE id = ? AND user_id = ?", (alert_id, user_id))


def list_email_enabled_for_cycle(conn: sqlite3.Connection):
    return conn.execute(
        """
        SELECT a.id, a.user_id, a.symbol, a.alert_type, a.threshold_value, a.direction,
               a.sentiment_label, a.last_notified_at, u.email
        FROM alerts a
        JOIN users u ON u.id = a.user_id
        WHERE a.is_enabled = 1 AND a.email_enabled = 1 AND u.status = 'approved'
        ORDER BY a.id ASC
        """
    ).fetchall()


def set_last_notified_at(conn: sqlite3.Connection, alert_id: int, timestamp: str) -> None:
    conn.execute("UPDATE alerts SET last_notified_at = ? WHERE id = ?", (timestamp, alert_id))
