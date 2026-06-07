import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from api.core.runtime import ALLOWED_ROLES, get_connection, normalize_symbol, now_utc, require_role, track_activity
from api.schemas.requests import ApprovalRequest, CryptoConfigRequest, ModelConfigRequest, RoleUpdateRequest

router = APIRouter(tags=["platform"])


@router.get("/admin/pending-users")
def admin_pending_users(admin: sqlite3.Row = Depends(require_role("admin"))):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, email, role, status, created_at FROM users WHERE status = 'pending' ORDER BY datetime(created_at) ASC"
        ).fetchall()
    finally:
        conn.close()

    return [dict(r) for r in rows]


@router.post("/admin/users/{user_id}/approval")
def admin_approve_user(
    user_id: int,
    payload: ApprovalRequest,
    admin: sqlite3.Row = Depends(require_role("admin")),
):
    status = "approved" if payload.approved else "rejected"
    conn = get_connection()
    try:
        target = conn.execute("SELECT id, email FROM users WHERE id = ?", (user_id,)).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="User not found.")
        conn.execute(
            "UPDATE users SET status = ?, approved_at = ?, approved_by = ? WHERE id = ?",
            (status, now_utc(), admin["id"], user_id),
        )
        conn.commit()
    finally:
        conn.close()

    track_activity(admin["id"], "admin.user.approval", f"Set user_id={user_id} status={status}")
    return {"message": f"User {status}.", "user_id": user_id, "status": status}


@router.get("/admin/users")
def admin_list_users(admin: sqlite3.Row = Depends(require_role("admin"))):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, email, role, status, created_at, approved_at FROM users ORDER BY id ASC"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


@router.patch("/admin/users/{user_id}/role")
def admin_update_role(
    user_id: int,
    payload: RoleUpdateRequest,
    admin: sqlite3.Row = Depends(require_role("admin")),
):
    role = payload.role.strip().lower()
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role.")

    conn = get_connection()
    try:
        target = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="User not found.")
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        conn.commit()
    finally:
        conn.close()

    track_activity(admin["id"], "admin.user.role.update", f"user_id={user_id}, role={role}")
    return {"message": "Role updated.", "user_id": user_id, "role": role}


@router.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: int, admin: sqlite3.Row = Depends(require_role("admin"))):
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Admin cannot delete own account.")

    conn = get_connection()
    try:
        target = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="User not found.")
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()

    track_activity(admin["id"], "admin.user.delete", f"Deleted user_id={user_id}")
    return {"message": "User deleted."}


@router.get("/admin/config/cryptos")
def admin_list_cryptos(admin: sqlite3.Row = Depends(require_role("admin"))):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, symbol, name, is_enabled, created_at FROM crypto_configs ORDER BY symbol"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


@router.post("/admin/config/cryptos")
def admin_upsert_crypto(
    payload: CryptoConfigRequest,
    admin: sqlite3.Row = Depends(require_role("admin")),
):
    symbol = normalize_symbol(payload.symbol)
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO crypto_configs (symbol, name, is_enabled, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                name = excluded.name,
                is_enabled = excluded.is_enabled
            """,
            (symbol, payload.name.strip(), int(payload.is_enabled), now_utc()),
        )
        conn.commit()
    finally:
        conn.close()

    track_activity(admin["id"], "admin.crypto.upsert", f"symbol={symbol}")
    return {"message": "Crypto configuration saved.", "symbol": symbol}


@router.get("/admin/config/models")
def admin_list_models(admin: sqlite3.Row = Depends(require_role("admin"))):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, model_name, is_enabled, is_researcher_available, created_at FROM model_configs ORDER BY model_name"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


@router.post("/admin/config/models")
def admin_upsert_model(
    payload: ModelConfigRequest,
    admin: sqlite3.Row = Depends(require_role("admin")),
):
    model_name = payload.model_name.strip().lower()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO model_configs (model_name, is_enabled, is_researcher_available, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(model_name) DO UPDATE SET
                is_enabled = excluded.is_enabled,
                is_researcher_available = excluded.is_researcher_available
            """,
            (model_name, int(payload.is_enabled), int(payload.is_researcher_available), now_utc()),
        )
        conn.commit()
    finally:
        conn.close()

    track_activity(admin["id"], "admin.model.upsert", f"model={model_name}")
    return {"message": "Model configuration saved.", "model_name": model_name}


@router.get("/admin/logs")
def admin_logs(admin: sqlite3.Row = Depends(require_role("admin"))):
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT l.id, l.user_id, u.email, l.action, l.details, l.created_at
            FROM activity_logs l
            LEFT JOIN users u ON u.id = l.user_id
            ORDER BY datetime(l.created_at) DESC
            LIMIT 200
            """
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


@router.get("/admin/api-usage")
def admin_api_usage(admin: sqlite3.Row = Depends(require_role("admin"))):
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT provider, endpoint, request_count, last_called_at, user_id
            FROM api_usage
            ORDER BY request_count DESC
            """
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]