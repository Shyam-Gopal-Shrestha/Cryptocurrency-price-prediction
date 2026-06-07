import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

import pyotp
from fastapi import APIRouter, Depends, Header, HTTPException

from api.core.runtime import (
	ALLOWED_REQUEST_ROLES,
	SESSION_HOURS,
	get_connection,
	get_current_user,
	get_user_by_email,
	hash_password,
	hash_session_token,
	normalize_email,
	now_utc,
	parse_bearer_token,
	track_activity,
	verify_password,
)
from api.schemas.requests import LoginRequest, SignupRequest, TwoFASetupResponse, TwoFAVerifyRequest

router = APIRouter(tags=["platform"])


@router.post("/signup")
def signup(payload: SignupRequest):
	role = payload.role.strip().lower()
	if role not in ALLOWED_REQUEST_ROLES:
		raise HTTPException(status_code=400, detail="Invalid role request.")

	email = normalize_email(payload.email)
	if len(payload.password.strip()) < 6:
		raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
	if get_user_by_email(email):
		raise HTTPException(status_code=409, detail="Email already registered.")

	conn = get_connection()
	try:
		cursor = conn.execute(
			"""
			INSERT INTO users (email, password_hash, role, status, created_at)
			VALUES (?, ?, ?, 'pending', ?)
			""",
			(email, hash_password(payload.password), role, now_utc()),
		)
		conn.commit()
		user_id = cursor.lastrowid
	finally:
		conn.close()

	track_activity(user_id, "user.signup", f"Requested role={role}")
	return {
		"message": "Registration submitted. Wait for admin approval.",
		"user": {"id": user_id, "email": email, "role": role, "status": "pending"},
	}


@router.post("/login")
def login(payload: LoginRequest):
	email = normalize_email(payload.email)
	user = get_user_by_email(email)
	if not user or not verify_password(payload.password, user["password_hash"]):
		raise HTTPException(status_code=401, detail="Invalid credentials.")
	if user["status"] != "approved":
		raise HTTPException(status_code=403, detail="Account pending admin approval.")

	if int(user["twofa_enabled"]) == 1:
		if not payload.otp_code:
			return {"requires_2fa": True, "message": "2FA code required."}
		normalized_otp = "".join(ch for ch in payload.otp_code if ch.isdigit())
		if len(normalized_otp) != 6:
			raise HTTPException(status_code=401, detail="Invalid 2FA code.")
		totp = pyotp.TOTP(user["twofa_secret"])
		if not totp.verify(normalized_otp, valid_window=2):
			raise HTTPException(status_code=401, detail="Invalid 2FA code.")

	raw_token = secrets.token_urlsafe(48)
	token_hash = hash_session_token(raw_token)
	expires_at = (datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)).isoformat()

	conn = get_connection()
	try:
		conn.execute(
			"""
			UPDATE sessions
			SET is_active = 0
			WHERE user_id = ? AND datetime(expires_at) <= datetime('now')
			""",
			(user["id"],),
		)
		conn.execute(
			"""
			INSERT INTO sessions (user_id, token, expires_at, created_at, is_active)
			VALUES (?, ?, ?, ?, 1)
			""",
			(user["id"], token_hash, expires_at, now_utc()),
		)
		conn.commit()
	finally:
		conn.close()

	track_activity(user["id"], "user.login", "User logged in.")
	return {
		"id": user["id"],
		"email": user["email"],
		"role": user["role"],
		"status": user["status"],
		"token": raw_token,
		"expires_at": expires_at,
	}


@router.post("/logout")
def logout(
	current_user: sqlite3.Row = Depends(get_current_user),
	authorization: Optional[str] = Header(default=None),
):
	raw_token = parse_bearer_token(authorization)
	token_hash = hash_session_token(raw_token)
	conn = get_connection()
	try:
		conn.execute(
			"UPDATE sessions SET is_active = 0 WHERE token = ? OR token = ?",
			(token_hash, raw_token),
		)
		conn.commit()
	finally:
		conn.close()

	track_activity(current_user["id"], "user.logout", "User logged out.")
	return {"message": "Logged out successfully."}


@router.post("/auth/logout-all")
def logout_all_sessions(current_user: sqlite3.Row = Depends(get_current_user)):
	conn = get_connection()
	try:
		conn.execute("UPDATE sessions SET is_active = 0 WHERE user_id = ?", (current_user["id"],))
		conn.commit()
	finally:
		conn.close()

	track_activity(current_user["id"], "user.logout_all", "All sessions revoked.")
	return {"message": "All sessions logged out."}


@router.get("/auth/me")
def auth_me(current_user: sqlite3.Row = Depends(get_current_user)):
	return {
		"id": current_user["id"],
		"email": current_user["email"],
		"role": current_user["role"],
		"status": current_user["status"],
		"twofa_enabled": bool(current_user["twofa_enabled"]),
	}


@router.post("/auth/2fa/setup", response_model=TwoFASetupResponse)
def setup_2fa(current_user: sqlite3.Row = Depends(get_current_user)):
	secret = pyotp.random_base32()
	app_name = "Crypto Prediction Platform"
	uri = pyotp.TOTP(secret).provisioning_uri(current_user["email"], issuer_name=app_name)

	conn = get_connection()
	try:
		conn.execute("UPDATE users SET twofa_secret = ? WHERE id = ?", (secret, current_user["id"]))
		conn.commit()
	finally:
		conn.close()

	track_activity(current_user["id"], "user.2fa.setup", "2FA setup initiated.")
	return TwoFASetupResponse(secret=secret, otpauth_uri=uri)


@router.post("/auth/2fa/enable")
def enable_2fa(payload: TwoFAVerifyRequest, current_user: sqlite3.Row = Depends(get_current_user)):
	if not current_user["twofa_secret"]:
		raise HTTPException(status_code=400, detail="Run setup first.")
	totp = pyotp.TOTP(current_user["twofa_secret"])
	if not totp.verify(payload.otp_code.strip(), valid_window=1):
		raise HTTPException(status_code=401, detail="Invalid OTP code.")

	conn = get_connection()
	try:
		conn.execute("UPDATE users SET twofa_enabled = 1 WHERE id = ?", (current_user["id"],))
		conn.commit()
	finally:
		conn.close()

	track_activity(current_user["id"], "user.2fa.enable", "2FA enabled.")
	return {"message": "2FA enabled."}


@router.post("/auth/2fa/disable")
def disable_2fa(current_user: sqlite3.Row = Depends(get_current_user)):
	conn = get_connection()
	try:
		conn.execute("UPDATE users SET twofa_enabled = 0, twofa_secret = NULL WHERE id = ?", (current_user["id"],))
		conn.commit()
	finally:
		conn.close()

	track_activity(current_user["id"], "user.2fa.disable", "2FA disabled.")
	return {"message": "2FA disabled."}
