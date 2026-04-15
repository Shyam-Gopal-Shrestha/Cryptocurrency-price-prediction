from sqlalchemy import Column, Integer, String, Enum, TIMESTAMP, text
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(30), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), default="")
    role = Column(Enum("user", "admin", "researcher"), nullable=False, default="user")
    status = Column(Enum("active", "inactive", "suspended"), nullable=False, default="active")
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
