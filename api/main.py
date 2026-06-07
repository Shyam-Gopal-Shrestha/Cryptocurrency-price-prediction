import asyncio
import contextlib
import logging
import os
from collections.abc import AsyncIterator
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import yfinance as yf
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.core import runtime as core_runtime
from api.core.runtime import (
    evaluate_alert_condition,
    get_connection,
    now_utc,
    require_role,
    track_activity,
    track_api_usage,
)
from api.routes.admin import router as admin_router
from api.routes.auth import router as auth_router
from api.routes.market import router as market_router
from api.routes.researcher import router as researcher_router
from api.routes.user import router as user_router
from api.services import alert_service, market_service
from api.services.market_service import (
    COIN_SYMBOL_MAP,
    EMAILJS_SEND_URL,
    NEGATIVE_WORDS,
    NEWS_FALLBACK,
    POSITIVE_WORDS,
    SYMBOL_KEYWORDS,
)

logger = logging.getLogger("uvicorn.error")
ALERT_EMAIL_INTERVAL_SECONDS = max(300, int(os.getenv("ALERT_EMAIL_INTERVAL_SECONDS", "3600")))


async def _alert_email_worker() -> None:
    while True:
        try:
            await asyncio.to_thread(_run_alert_email_cycle)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Background alert email worker failed")

        try:
            await asyncio.sleep(300)
        except asyncio.CancelledError:
            raise


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(_alert_email_worker())
    app.state.alert_email_task = task
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        app.state.alert_email_task = None


app = FastAPI(title="Crypto Price Prediction API", version="1.0.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(researcher_router)
app.include_router(user_router)
app.include_router(market_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_app() -> FastAPI:
    return app


def _sync_market_service_io() -> None:
    market_service.urlopen = urlopen
    market_service.Request = Request
    market_service.HTTPError = HTTPError


@app.get("/")
def home():
    return {"message": "Crypto Price Prediction API Running"}


@app.get("/health")
def health():
    return {"status": "ok"}


def _symbol_to_coin_id(symbol: str) -> str:
    return market_service.symbol_to_coin_id(symbol)


def _symbol_code(symbol: str) -> str:
    return market_service.symbol_code(symbol)


def _news_items_for_coin(coin: str):
    return market_service.news_items_for_coin(coin)


def _fetch_google_news_rss(coin_id: str, code: str, limit: int = 10) -> tuple[list[dict], str]:
    _sync_market_service_io()
    return market_service.fetch_google_news_rss(coin_id, code, limit)


def _analyze_text_sentiment(text: str) -> dict:
    return market_service.analyze_text_sentiment(text)


def _aggregate_sentiment(items: list[dict]) -> dict:
    return market_service.aggregate_sentiment(items)


def _extract_nitter_rss_tweets(query: str, limit: int = 10) -> tuple[list[dict], str]:
    _sync_market_service_io()
    return market_service.extract_nitter_rss_tweets(query, limit)


def _extract_x_api_tweets(query: str, limit: int = 10) -> tuple[list[dict], str]:
    _sync_market_service_io()
    return market_service.extract_x_api_tweets(query, limit)


def _parse_iso_datetime(value: str | None):
    return market_service.parse_iso_datetime(value)


def _should_send_alert_email(last_notified_at: str | None) -> bool:
    return market_service.should_send_alert_email(last_notified_at, ALERT_EMAIL_INTERVAL_SECONDS)


def _get_symbol_sentiment_label(symbol: str) -> str | None:
    return market_service.get_symbol_sentiment_label(
        symbol,
        _fetch_google_news_rss,
        _news_items_for_coin,
        _analyze_text_sentiment,
        _aggregate_sentiment,
        _extract_x_api_tweets,
        _extract_nitter_rss_tweets,
    )


def _send_emailjs_alert(alert: dict, recipient_email: str) -> tuple[bool, str]:
    _sync_market_service_io()
    return market_service.send_emailjs_alert(alert, recipient_email, now_utc)


def _run_alert_email_cycle() -> None:
    return alert_service.run_alert_email_cycle(
        get_connection,
        core_runtime.get_latest_price_and_change,
        _get_symbol_sentiment_label,
        evaluate_alert_condition,
        _should_send_alert_email,
        _send_emailjs_alert,
        track_api_usage,
        track_activity,
        now_utc,
        logger,
    )


def get_coin_news(
    symbol: str = "BTC-USD",
    coin: str | None = None,
    current_user=Depends(require_role("user", "researcher", "admin")),
):
    requested_symbol = coin or symbol
    coin_id = _symbol_to_coin_id(requested_symbol)
    code = _symbol_code(requested_symbol)
    user_id = current_user.get("id") if isinstance(current_user, dict) else current_user["id"]
    track_api_usage("google_news", "coin_news", user_id)
    items, _ = _fetch_google_news_rss(coin_id, code, limit=8)
    return items or _news_items_for_coin(coin_id)


def get_sentiment_summary(
    symbol: str = "BTC-USD",
    limit: int = 10,
    current_user=Depends(require_role("user", "researcher", "admin")),
):
    user_id = current_user.get("id") if isinstance(current_user, dict) else current_user["id"]
    track_api_usage("market_intelligence", "sentiment_summary", user_id)

    limit = max(1, min(int(limit), 50))
    coin_id = _symbol_to_coin_id(symbol)
    code = _symbol_code(symbol)

    news_raw, news_source = _fetch_google_news_rss(coin_id, code, limit=limit)
    if news_raw:
        news_items = []
        for item in news_raw[:limit]:
            sentiment = _analyze_text_sentiment(f"{item.get('title', '')} {item.get('summary', '')}")
            news_items.append({**item, "sentiment_score": sentiment["score"], "sentiment_label": sentiment["label"]})
        news_output_source = news_source
    else:
        news_items = []
        for item in _news_items_for_coin(coin_id)[:limit]:
            sentiment = _analyze_text_sentiment(f"{item.get('title', '')} {item.get('summary', '')}")
            news_items.append({**item, "sentiment_score": sentiment["score"], "sentiment_label": sentiment["label"]})
        news_output_source = "curated-fallback" if news_items else news_source

    keyword = " OR ".join(SYMBOL_KEYWORDS.get(code, [code.lower()])) + " lang:en"
    tweets, twitter_source = _extract_x_api_tweets(keyword, limit=limit)
    if not tweets:
        tweets, twitter_source = _extract_nitter_rss_tweets(f"{code} OR {coin_id} lang:en", limit=limit)

    twitter_items = []
    for item in tweets[:limit]:
        sentiment = _analyze_text_sentiment(item.get("text", ""))
        twitter_items.append({**item, "sentiment_score": sentiment["score"], "sentiment_label": sentiment["label"]})

    summaries = []
    if news_items:
        summaries.append(_aggregate_sentiment(news_items))
    if twitter_items:
        summaries.append(_aggregate_sentiment(twitter_items))

    if summaries:
        overall_score = sum(item["score"] for item in summaries) / len(summaries)
        if overall_score > 0.12:
            overall_label = "positive"
        elif overall_score < -0.12:
            overall_label = "negative"
        else:
            overall_label = "neutral"
        overall = {"label": overall_label, "score": float(overall_score)}
    else:
        overall = {"label": "neutral", "score": 0.0}

    return {
        "symbol": symbol,
        "news": {
            "source": news_output_source,
            "items": news_items,
            "summary": _aggregate_sentiment(news_items) if news_items else {"score": 0.0, "label": "neutral", "count": 0},
        },
        "twitter": {
            "source": twitter_source,
            "items": twitter_items,
            "summary": _aggregate_sentiment(twitter_items) if twitter_items else {"score": 0.0, "label": "neutral", "count": 0},
            "is_configured": bool((os.getenv("TWITTER_BEARER_TOKEN") or "").strip()),
        },
        "overall": overall,
    }


def get_live_market(
    symbol: str = "BTC-USD",
    days: int = 1,
    current_user=Depends(require_role("user", "researcher", "admin")),
):
    user_id = current_user.get("id") if isinstance(current_user, dict) else current_user["id"]
    track_api_usage("market_data", "live_market", user_id)
    try:
        _sync_market_service_io()
        return market_service.get_live_market(symbol, days, yf)
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Live market data is temporarily unavailable from upstream providers.",
        )
