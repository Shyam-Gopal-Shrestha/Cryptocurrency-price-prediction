from datetime import datetime

import pytest

import api.auth as auth


class DummyCursor:
    def __init__(self, one=None, all_rows=None):
        self._one = one
        self._all_rows = all_rows or []

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._all_rows


class DummyConn:
    def __init__(self, query_map=None):
        self.query_map = query_map or {}
        self.executed = []
        self.closed = False
        self.committed = False

    def execute(self, sql, params=()):
        self.executed.append((sql, params))
        key = next((k for k in self.query_map if k in sql), None)
        result = self.query_map.get(key, {})
        return DummyCursor(one=result.get("one"), all_rows=result.get("all", []))

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def test_get_connection_and_now_utc(monkeypatch, tmp_path):
    db_file = tmp_path / "auth_test.db"
    monkeypatch.setattr(auth, "DB_PATH", str(db_file))
    conn = auth.get_connection()
    try:
        assert conn.row_factory is not None
    finally:
        conn.close()

    ts = auth.now_utc()
    assert isinstance(ts, str)
    assert datetime.fromisoformat(ts)


def test_normalize_email_and_symbol():
    assert auth.normalize_email(" USER@Example.COM ") == "user@example.com"

    with pytest.raises(auth.HTTPException) as exc:
        auth.normalize_email("invalid")
    assert exc.value.status_code == 400

    assert auth.normalize_symbol("btc") == "BTC-USD"
    assert auth.normalize_symbol("eth-usd") == "ETH-USD"

    with pytest.raises(auth.HTTPException) as exc:
        auth.normalize_symbol("   ")
    assert exc.value.status_code == 400


def test_parse_bearer_token():
    with pytest.raises(auth.HTTPException) as exc:
        auth.parse_bearer_token(None)
    assert exc.value.status_code == 401

    with pytest.raises(auth.HTTPException) as exc:
        auth.parse_bearer_token("Token abc")
    assert exc.value.status_code == 401

    assert auth.parse_bearer_token("Bearer my-token ") == "my-token"


def test_password_hash_and_verify(monkeypatch):
    hashed = auth.hash_password("secret")
    assert hashed and hashed != "secret"
    assert auth.verify_password("secret", hashed)
    assert not auth.verify_password("wrong", hashed)

    monkeypatch.setattr(auth.pwd_context, "verify", lambda p, h: (_ for _ in ()).throw(RuntimeError("fail")))
    assert auth.verify_password("secret", hashed) is False


def test_tracking_helpers(monkeypatch):
    conn1 = DummyConn()
    conn2 = DummyConn(query_map={"SELECT id, request_count FROM api_usage": {"one": {"id": 7, "request_count": 2}}})
    conn3 = DummyConn(query_map={"SELECT id, request_count FROM api_usage": {"one": None}})
    conns = [conn1, conn2, conn3]
    monkeypatch.setattr(auth, "get_connection", lambda: conns.pop(0))
    monkeypatch.setattr(auth, "now_utc", lambda: "2026-01-01T00:00:00+00:00")

    auth.track_activity(1, "test.action", "details")
    assert conn1.committed and conn1.closed
    assert any("INSERT INTO activity_logs" in sql for sql, _ in conn1.executed)

    auth.track_api_usage("cg", "/price", 1)
    assert conn2.committed and conn2.closed
    assert any("UPDATE api_usage" in sql for sql, _ in conn2.executed)

    auth.track_api_usage("cg", "/price", 1)
    assert conn3.committed and conn3.closed
    assert any("INSERT INTO api_usage" in sql for sql, _ in conn3.executed)


def test_get_user_by_email_and_hash_session(monkeypatch):
    expected = {"id": 10, "email": "user@example.com"}
    conn = DummyConn(query_map={"SELECT * FROM users WHERE email = ?": {"one": expected}})
    monkeypatch.setattr(auth, "get_connection", lambda: conn)

    row = auth.get_user_by_email("user@example.com")
    assert row == expected
    assert conn.closed

    digest = auth.hash_session_token("abc")
    assert len(digest) == 64
    assert digest == auth.hash_session_token("abc")


def test_get_gemini_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert auth.get_gemini_api_key() is None

    monkeypatch.setenv("GEMINI_API_KEY", " 'good-key' ")
    assert auth.get_gemini_api_key() == "good-key"

    monkeypatch.setenv("GEMINI_API_KEY", "changeme")
    assert auth.get_gemini_api_key() is None


def test_get_current_user_and_require_role(monkeypatch):
    approved = {"id": 1, "status": "approved", "role": "admin"}
    pending = {"id": 2, "status": "pending", "role": "user"}

    conn_ok = DummyConn(query_map={"SELECT u.*": {"one": approved}})
    monkeypatch.setattr(auth, "parse_bearer_token", lambda v: "token")
    monkeypatch.setattr(auth, "hash_session_token", lambda v: "hash")
    monkeypatch.setattr(auth, "get_connection", lambda: conn_ok)

    row = auth.get_current_user("Bearer token")
    assert row == approved
    assert conn_ok.closed

    conn_none = DummyConn(query_map={"SELECT u.*": {"one": None}})
    monkeypatch.setattr(auth, "get_connection", lambda: conn_none)
    with pytest.raises(auth.HTTPException) as exc:
        auth.get_current_user("Bearer token")
    assert exc.value.status_code == 401

    conn_pending = DummyConn(query_map={"SELECT u.*": {"one": pending}})
    monkeypatch.setattr(auth, "get_connection", lambda: conn_pending)
    with pytest.raises(auth.HTTPException) as exc:
        auth.get_current_user("Bearer token")
    assert exc.value.status_code == 403

    dep = auth.require_role("admin")
    assert dep(approved) == approved
    with pytest.raises(auth.HTTPException) as exc:
        dep({"role": "user"})
    assert exc.value.status_code == 403


def test_table_columns_and_schema_helpers():
    conn = DummyConn(
        query_map={
            "PRAGMA table_info(users)": {"all": [{"name": "id"}, {"name": "status"}]},
            "PRAGMA table_info(alerts)": {"all": [{"name": "id"}, {"name": "last_notified_at"}]},
        }
    )

    cols = auth.table_columns(conn, "users")
    assert "id" in cols and "status" in cols

    conn_missing_users = DummyConn(query_map={"PRAGMA table_info(users)": {"all": [{"name": "id"}]}})
    auth.ensure_users_schema(conn_missing_users)
    sql_joined = "\n".join(sql for sql, _ in conn_missing_users.executed)
    assert "ALTER TABLE users ADD COLUMN status" in sql_joined
    assert "ALTER TABLE users ADD COLUMN twofa_secret" in sql_joined
    assert "UPDATE users SET status = 'approved'" in sql_joined

    conn_missing_alerts = DummyConn(query_map={"PRAGMA table_info(alerts)": {"all": [{"name": "id"}]}})
    auth.ensure_alerts_schema(conn_missing_alerts)
    sql_joined = "\n".join(sql for sql, _ in conn_missing_alerts.executed)
    assert "ALTER TABLE alerts ADD COLUMN email_enabled" in sql_joined
    assert "ALTER TABLE alerts ADD COLUMN last_notified_at" in sql_joined
    assert "UPDATE alerts SET email_enabled = 1" in sql_joined
