from typing import List, Optional

from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    email: str
    password: str
    role: str = "user"


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)
    otp_code: Optional[str] = None


class RoleUpdateRequest(BaseModel):
    role: str


class ApprovalRequest(BaseModel):
    approved: bool = True


class CryptoConfigRequest(BaseModel):
    symbol: str
    name: str
    is_enabled: bool = True


class ModelConfigRequest(BaseModel):
    model_name: str
    is_enabled: bool = True
    is_researcher_available: bool = True


class DataFetchRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    interval: str = "1d"


class PreprocessRequest(BaseModel):
    symbol: str
    fast_window: int = 7
    slow_window: int = 21


class TrainRequest(BaseModel):
    symbol: str
    models: List[str] = Field(
        default_factory=lambda: [
            "linear_regression",
            "random_forest",
            "xgboost",
            "svr",
            "lstm",
            "gru",
            "transformer",
        ]
    )
    horizon: int = 1
    test_size: float = 0.2
    auto_deploy_best: bool = True


class PredictionRequest(BaseModel):
    symbol: str
    horizon: int = 1
    explanation_mode: str = "simple"
    risk_tolerance: str = "medium"


class TwoFASetupResponse(BaseModel):
    secret: str
    otpauth_uri: str


class TwoFAVerifyRequest(BaseModel):
    otp_code: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = Field(default_factory=list)


class AlertCreateRequest(BaseModel):
    symbol: str
    alert_type: str = "target"
    threshold_value: Optional[float] = None
    direction: str = "above"
    sentiment_label: Optional[str] = None
    is_enabled: bool = True
    email_enabled: bool = True


class AlertUpdateRequest(BaseModel):
    is_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None


class PortfolioHoldingRequest(BaseModel):
    symbol: str
    quantity: float = Field(gt=0)
    avg_buy_price: float = Field(gt=0)