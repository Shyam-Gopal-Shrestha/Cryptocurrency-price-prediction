import re
from pydantic import BaseModel, EmailStr, field_validator


class RegisterSchema(BaseModel):
    fullname: str
    email: EmailStr
    password: str
    confirmPassword: str
    role: str

    @field_validator("fullname")
    @classmethod
    def validate_fullname(cls, value: str) -> str:
        if not re.match(r"^[A-Za-z' -]{2,}$", value):
            raise ValueError("Invalid full name")
        return value

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in ["user", "admin", "researcher"]:
            raise ValueError("Invalid role")
        return value


class LoginSchema(BaseModel):
    email: EmailStr
    password: str
