import sqlite3


def get_latest_deployed_for_symbol(conn: sqlite3.Connection, symbol: str):
    return conn.execute(
        """
        SELECT id, model_name, artifact_path
        FROM experiments
        WHERE symbol = ? AND is_deployed = 1
        ORDER BY datetime(created_at) DESC
        LIMIT 1
        """,
        (symbol,),
    ).fetchone()


def list_recent(conn: sqlite3.Connection):
    return conn.execute(
        """
        SELECT id, researcher_id, symbol, model_name, metrics_json, artifact_path, status, is_deployed, created_at
        FROM experiments
        ORDER BY datetime(created_at) DESC
        LIMIT 200
        """
    ).fetchall()
