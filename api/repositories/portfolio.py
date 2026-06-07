import sqlite3


def list_by_user(conn: sqlite3.Connection, user_id: int):
    return conn.execute(
        """
        SELECT id, symbol, quantity, avg_buy_price, created_at, updated_at
        FROM portfolio_holdings
        WHERE user_id = ?
        ORDER BY symbol ASC
        """,
        (user_id,),
    ).fetchall()


def find_by_user_and_symbol(conn: sqlite3.Connection, user_id: int, symbol: str):
    return conn.execute(
        "SELECT id FROM portfolio_holdings WHERE user_id = ? AND symbol = ?",
        (user_id, symbol),
    ).fetchone()


def update_holding(conn: sqlite3.Connection, quantity: float, avg_buy_price: float, updated_at: str, user_id: int, symbol: str):
    conn.execute(
        """
        UPDATE portfolio_holdings
        SET quantity = ?, avg_buy_price = ?, updated_at = ?
        WHERE user_id = ? AND symbol = ?
        """,
        (quantity, avg_buy_price, updated_at, user_id, symbol),
    )


def create_holding(conn: sqlite3.Connection, user_id: int, symbol: str, quantity: float, avg_buy_price: float, created_at: str):
    conn.execute(
        """
        INSERT INTO portfolio_holdings (user_id, symbol, quantity, avg_buy_price, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, symbol, quantity, avg_buy_price, created_at, created_at),
    )


def delete_by_user_and_symbol(conn: sqlite3.Connection, user_id: int, symbol: str) -> None:
    conn.execute("DELETE FROM portfolio_holdings WHERE user_id = ? AND symbol = ?", (user_id, symbol))
