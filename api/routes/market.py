from fastapi import APIRouter, Depends

from api.core.runtime import require_role

router = APIRouter(tags=["platform"])


@router.get("/news")
@router.get("/api/coin-news")
def get_coin_news(
    symbol: str = "BTC-USD",
    coin: str | None = None,
    current_user=Depends(require_role("user", "researcher", "admin")),
):
    from api import main

    return main.get_coin_news(symbol=symbol, coin=coin, current_user=current_user)


@router.get("/sentiment-summary")
@router.get("/api/sentiment")
def get_sentiment_summary(
    symbol: str = "BTC-USD",
    limit: int = 10,
    current_user=Depends(require_role("user", "researcher", "admin")),
):
    from api import main

    return main.get_sentiment_summary(symbol=symbol, limit=limit, current_user=current_user)


@router.get("/live-market")
@router.get("/api/live-market")
def get_live_market(
    symbol: str = "BTC-USD",
    days: int = 1,
    current_user=Depends(require_role("user", "researcher", "admin")),
):
    from api import main

    return main.get_live_market(symbol=symbol, days=days, current_user=current_user)
