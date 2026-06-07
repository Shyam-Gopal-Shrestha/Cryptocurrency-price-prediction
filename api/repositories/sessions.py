import sqlite3


def get_user_by_token(conn: sqlite3.Connection, token_hash: str, raw_token: str):
    return conn.execute(
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


def deactivate_by_token(conn: sqlite3.Connection, token_hash: str, raw_token: str) -> None:
    conn.execute("UPDATE sessions SET is_active = 0 WHERE token = ? OR token = ?", (token_hash, raw_token))


def deactivate_all_for_user(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute("UPDATE sessions SET is_active = 0 WHERE user_id = ?", (user_id,))
