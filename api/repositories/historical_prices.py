import sqlite3


def list_for_symbol(conn: sqlite3.Connection, symbol: str):
    return conn.execute(
        """
        SELECT timestamp, open, high, low, close, volume
        FROM historical_prices
        WHERE symbol = ?
        ORDER BY datetime(timestamp) ASC
        """,
        (symbol,),
    ).fetchall()


def list_latest_closes(conn: sqlite3.Connection, symbol: str):
    return conn.execute(
        """
        SELECT close
        FROM historical_prices
        WHERE symbol = ?
        ORDER BY datetime(timestamp) DESC
        LIMIT 2
        """,
        (symbol,),
    ).fetchall()
