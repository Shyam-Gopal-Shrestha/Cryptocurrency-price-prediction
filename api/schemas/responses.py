from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str


class AuthMeResponse(BaseModel):
    id: int
    email: str
    role: str
    status: str
    twofa_enabled: bool
