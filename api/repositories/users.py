import sqlite3


def get_by_email(conn: sqlite3.Connection, email: str):
    return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def get_by_id(conn: sqlite3.Connection, user_id: int):
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def list_pending(conn: sqlite3.Connection):
    return conn.execute(
        "SELECT id, email, role, status, created_at FROM users WHERE status = 'pending' ORDER BY datetime(created_at) ASC"
    ).fetchall()


def list_all(conn: sqlite3.Connection):
    return conn.execute(
        "SELECT id, email, role, status, created_at, approved_at FROM users ORDER BY id ASC"
    ).fetchall()
