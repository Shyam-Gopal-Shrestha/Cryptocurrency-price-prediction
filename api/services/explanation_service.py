from api.services import ml_service


def generate_explanation(
    symbol: str,
    horizon: int,
    predicted_price: float,
    trend: str,
    confidence: float,
    mode: str,
    last_close: float,
    get_gemini_api_key_fn,
):
    return ml_service.generate_explanation(
        symbol,
        horizon,
        predicted_price,
        trend,
        confidence,
        mode,
        last_close,
        get_gemini_api_key_fn,
    )
