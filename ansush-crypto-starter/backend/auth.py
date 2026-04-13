from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
from schemas import RegisterSchema, LoginSchema
import re
import bcrypt

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register")
def register(data: RegisterSchema, db: Session = Depends(get_db)):
    if data.password != data.confirmPassword:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&]).{8,72}$", data.password):
        raise HTTPException(status_code=400, detail="Weak password")

    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")

    parts = data.fullname.strip().split()
    first_name = parts[0]
    last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    base_username = re.sub(r"[^A-Za-z0-9_]", "_", data.email.split("@")[0])[:30] or "user"
    username = base_username
    counter = 1

    while db.query(User).filter(User.username == username).first():
        username = f"{base_username[:28]}{counter}"
        counter += 1

    hashed_password = bcrypt.hashpw(
        data.password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    new_user = User(
        username=username,
        email=data.email,
        password_hash=hashed_password,
        first_name=first_name,
        last_name=last_name,
        role=data.role,
        status="active"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "ok": True,
        "message": "Registration successful",
        "username": new_user.username,
        "role": new_user.role
    }

@router.post("/login")
def login(data: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Email not found")

    if user.status != "active":
        raise HTTPException(status_code=403, detail="Account is not active")

    if not bcrypt.checkpw(
        data.password.encode("utf-8"),
        user.password_hash.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Incorrect password")

    return {
        "ok": True,
        "message": "Login successful",
        "username": user.username,
        "role": user.role
    }