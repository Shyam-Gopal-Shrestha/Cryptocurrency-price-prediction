import asyncio
import json

import pytest
from fastapi.testclient import TestClient

import api.auth as auth
import api.main as main


class DummyResponse:
    def __init__(self, payload: bytes, status: int = 200):
        self._payload = payload
        self.status = status

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def client(monkeypatch):
    async def fake_worker():
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            raise

    monkeypatch.setattr(main, "_alert_email_worker", fake_worker)
    main.app.dependency_overrides[auth.get_current_user] = lambda: {
        "id": 1,
        "email": "admin@example.com",
        "role": "admin",
        "status": "approved",
    }

    with TestClient(main.app) as test_client:
        yield test_client

    main.app.dependency_overrides.clear()


@pytest.mark.integration
def test_health_endpoints(client):
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["message"]

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}


@pytest.mark.integration
def test_coin_news_endpoint_with_live_source(client, monkeypatch):
    monkeypatch.setattr(
        main,
        "_fetch_google_news_rss",
        lambda coin_id, code, limit=8: ([{"title": "Live Item", "url": "https://news", "source": "Google"}], "google-news-rss"),
    )

    res = client.get("/api/coin-news", params={"coin": "BTC"})
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["title"] == "Live Item"


@pytest.mark.integration
def test_coin_news_endpoint_fallback(client, monkeypatch):
    monkeypatch.setattr(main, "_fetch_google_news_rss", lambda coin_id, code, limit=8: ([], "unavailable"))

    res = client.get("/api/coin-news", params={"coin": "BTC"})
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list)
    assert body


@pytest.mark.integration
def test_sentiment_endpoint(client, monkeypatch):
    monkeypatch.setattr(
        main,
        "_fetch_google_news_rss",
        lambda coin_id, code, limit=10: ([{"title": "bullish rally", "summary": "strong gain", "url": "https://n", "source": "news"}], "google-news-rss"),
    )
    monkeypatch.setattr(
        main,
        "_extract_x_api_tweets",
        lambda query, limit=10: ([{"text": "uptrend breakout", "url": "https://t", "created_at": "now", "source": "twitter-api"}], "twitter-api"),
    )

    res = client.get("/api/sentiment", params={"symbol": "BTC-USD", "limit": 10})
    assert res.status_code == 200
    body = res.json()
    assert body["symbol"] == "BTC-USD"
    assert "overall" in body
    assert "news" in body
    assert "twitter" in body


@pytest.mark.integration
def test_live_market_endpoint(client, monkeypatch):
    chart_payload = json.dumps({"prices": [[1700000000000, 100.0], [1700003600000, 101.0]]}).encode("utf-8")
    price_payload = json.dumps({"bitcoin": {"usd": 102.0}}).encode("utf-8")

    calls = {"n": 0}

    def fake_urlopen(req, timeout=12):
        calls["n"] += 1
        if calls["n"] == 1:
            return DummyResponse(chart_payload)
        return DummyResponse(price_payload)

    monkeypatch.setattr(main, "urlopen", fake_urlopen)

    res = client.get("/api/live-market", params={"symbol": "BTC-USD", "days": 1})
    assert res.status_code == 200
    body = res.json()
    assert body["source"] == "coingecko"
    assert body["current_price"] == 102.0
    assert len(body["prices"]) == 2
