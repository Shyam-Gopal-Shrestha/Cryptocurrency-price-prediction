import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def ensure_users_schema(conn: sqlite3.Connection) -> None:
    existing = table_columns(conn, "users")

    if "status" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'approved'")
    if "twofa_secret" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN twofa_secret TEXT")
    if "twofa_enabled" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN twofa_enabled INTEGER NOT NULL DEFAULT 0")
    if "approved_at" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN approved_at TEXT")
    if "approved_by" not in existing:
        conn.execute("ALTER TABLE users ADD COLUMN approved_by INTEGER")

    conn.execute("UPDATE users SET status = 'approved' WHERE status IS NULL OR status = ''")


def ensure_alerts_schema(conn: sqlite3.Connection) -> None:
    existing = table_columns(conn, "alerts")

    if "email_enabled" not in existing:
        conn.execute("ALTER TABLE alerts ADD COLUMN email_enabled INTEGER NOT NULL DEFAULT 1")
    if "last_notified_at" not in existing:
        conn.execute("ALTER TABLE alerts ADD COLUMN last_notified_at TEXT")

    conn.execute("UPDATE alerts SET email_enabled = 1 WHERE email_enabled IS NULL")


def has_foreign_key(conn: sqlite3.Connection, table_name: str, from_col: str, ref_table: str, ref_col: str) -> bool:
    rows = conn.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()
    return any(
        row["from"] == from_col and row["table"] == ref_table and row["to"] == ref_col
        for row in rows
    )


def backfill_config_references(conn: sqlite3.Connection, now_utc_fn: Callable[[], str]) -> None:
    # Ensure every symbol used in data tables exists in crypto_configs before enforcing FK constraints.
    conn.execute(
        """
        INSERT OR IGNORE INTO crypto_configs (symbol, name, is_enabled, created_at)
        SELECT DISTINCT symbol, symbol, 1, ?
        FROM historical_prices
        WHERE symbol IS NOT NULL AND TRIM(symbol) <> ''
        """,
        (now_utc_fn(),),
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO crypto_configs (symbol, name, is_enabled, created_at)
        SELECT DISTINCT symbol, symbol, 1, ?
        FROM experiments
        WHERE symbol IS NOT NULL AND TRIM(symbol) <> ''
        """,
        (now_utc_fn(),),
    )

    # Ensure every model referenced by experiments exists in model_configs before enforcing FK constraints.
    conn.execute(
        """
        INSERT OR IGNORE INTO model_configs (model_name, is_enabled, is_researcher_available, created_at)
        SELECT DISTINCT model_name, 1, 1, ?
        FROM experiments
        WHERE model_name IS NOT NULL AND TRIM(model_name) <> ''
        """,
        (now_utc_fn(),),
    )


def migrate_historical_prices_fk(conn: sqlite3.Connection) -> None:
    conn.execute("ALTER TABLE historical_prices RENAME TO historical_prices_old")
    conn.execute(
        """
        CREATE TABLE historical_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(symbol, timestamp),
            FOREIGN KEY(symbol) REFERENCES crypto_configs(symbol)
        )
        """
    )
    conn.execute(
        """
        INSERT INTO historical_prices (id, symbol, timestamp, open, high, low, close, volume, source, created_at)
        SELECT id, symbol, timestamp, open, high, low, close, volume, source, created_at
        FROM historical_prices_old
        """
    )
    conn.execute("DROP TABLE historical_prices_old")


def migrate_experiments_fk(conn: sqlite3.Connection) -> None:
    conn.execute("ALTER TABLE experiments RENAME TO experiments_old")
    conn.execute(
        """
        CREATE TABLE experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            researcher_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            model_name TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            artifact_path TEXT NOT NULL,
            status TEXT NOT NULL,
            is_deployed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(researcher_id) REFERENCES users(id),
            FOREIGN KEY(symbol) REFERENCES crypto_configs(symbol),
            FOREIGN KEY(model_name) REFERENCES model_configs(model_name)
        )
        """
    )
    conn.execute(
        """
        INSERT INTO experiments (id, researcher_id, symbol, model_name, metrics_json, artifact_path, status, is_deployed, created_at)
        SELECT id, researcher_id, symbol, model_name, metrics_json, artifact_path, status, is_deployed, created_at
        FROM experiments_old
        """
    )
    conn.execute("DROP TABLE experiments_old")


def ensure_reference_constraints(conn: sqlite3.Connection, now_utc_fn: Callable[[], str]) -> None:
    backfill_config_references(conn, now_utc_fn)

    if not has_foreign_key(conn, "historical_prices", "symbol", "crypto_configs", "symbol"):
        migrate_historical_prices_fk(conn)

    has_symbol_fk = has_foreign_key(conn, "experiments", "symbol", "crypto_configs", "symbol")
    has_model_fk = has_foreign_key(conn, "experiments", "model_name", "model_configs", "model_name")
    if not has_symbol_fk or not has_model_fk:
        migrate_experiments_fk(conn)


def bootstrap_admin(
    get_connection_fn: Callable[[], sqlite3.Connection],
    normalize_email_fn: Callable[[str], str],
    hash_password_fn: Callable[[str], str],
    now_utc_fn: Callable[[], str],
) -> None:
    admin_email = os.getenv("ADMIN_EMAIL", "admin@local.dev")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    conn = get_connection_fn()
    try:
        existing_admin = conn.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1").fetchone()
        if existing_admin:
            return

        conn.execute(
            """
            INSERT INTO users (email, password_hash, role, status, created_at, approved_at)
            VALUES (?, ?, 'admin', 'approved', ?, ?)
            """,
            (normalize_email_fn(admin_email), hash_password_fn(admin_password), now_utc_fn(), now_utc_fn()),
        )
        conn.commit()
    finally:
        conn.close()


def init_auth_db(
    get_connection_fn: Callable[[], sqlite3.Connection],
    now_utc_fn: Callable[[], str],
    model_storage_dir: Path,
    normalize_email_fn: Callable[[str], str],
    hash_password_fn: Callable[[str], str],
) -> None:
    conn = get_connection_fn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                status TEXT NOT NULL DEFAULT 'pending',
                twofa_secret TEXT,
                twofa_enabled INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                approved_at TEXT,
                approved_by INTEGER
            )
            """
        )
        ensure_users_schema(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS crypto_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                is_enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS model_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT UNIQUE NOT NULL,
                is_enabled INTEGER NOT NULL DEFAULT 1,
                is_researcher_available INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS historical_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(symbol, timestamp),
                FOREIGN KEY(symbol) REFERENCES crypto_configs(symbol)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                researcher_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                model_name TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                artifact_path TEXT NOT NULL,
                status TEXT NOT NULL,
                is_deployed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(researcher_id) REFERENCES users(id),
                FOREIGN KEY(symbol) REFERENCES crypto_configs(symbol),
                FOREIGN KEY(model_name) REFERENCES model_configs(model_name)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prediction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                horizon INTEGER NOT NULL,
                predicted_price REAL NOT NULL,
                trend TEXT NOT NULL,
                confidence REAL NOT NULL,
                explanation_mode TEXT NOT NULL,
                explanation TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                user_id INTEGER,
                request_count INTEGER NOT NULL DEFAULT 1,
                last_called_at TEXT NOT NULL,
                UNIQUE(provider, endpoint),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                threshold_value REAL,
                direction TEXT NOT NULL DEFAULT 'above',
                sentiment_label TEXT,
                is_enabled INTEGER NOT NULL DEFAULT 1,
                email_enabled INTEGER NOT NULL DEFAULT 1,
                last_notified_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        ensure_alerts_schema(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolio_holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                quantity REAL NOT NULL,
                avg_buy_price REAL NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, symbol),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.commit()

        model_storage_dir.mkdir(parents=True, exist_ok=True)

        default_cryptos = [
            ("BTC-USD", "Bitcoin"),
            ("ETH-USD", "Ethereum"),
            ("SOL-USD", "Solana"),
            ("ADA-USD", "Cardano"),
        ]
        for symbol, name in default_cryptos:
            conn.execute(
                """
                INSERT OR IGNORE INTO crypto_configs (symbol, name, is_enabled, created_at)
                VALUES (?, ?, 1, ?)
                """,
                (symbol, name, now_utc_fn()),
            )

        default_models = [
            "linear_regression",
            "random_forest",
            "xgboost",
            "svr",
            "lstm",
            "gru",
            "transformer",
        ]
        for model in default_models:
            conn.execute(
                """
                INSERT OR IGNORE INTO model_configs (model_name, is_enabled, is_researcher_available, created_at)
                VALUES (?, 1, 1, ?)
                """,
                (model, now_utc_fn()),
            )

        conn.execute(
            """
            UPDATE model_configs
            SET is_enabled = 1, is_researcher_available = 1
            WHERE model_name IN ('linear_regression', 'random_forest', 'xgboost', 'svr', 'lstm', 'gru', 'transformer')
            """
        )

        ensure_reference_constraints(conn, now_utc_fn)
        conn.commit()
    finally:
        conn.close()

    bootstrap_admin(get_connection_fn, normalize_email_fn, hash_password_fn, now_utc_fn)
