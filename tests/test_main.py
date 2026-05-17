import asyncio
import io
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.error import HTTPError

import pandas as pd
import pytest

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


class QueryCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class DummyConn:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.executed = []
        self.closed = False
        self.committed = False

    def execute(self, sql, params=()):
        self.executed.append((sql, params))
        if "SELECT a.id" in sql:
            return QueryCursor(self.rows)
        return QueryCursor([])

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def test_health_and_home():
    assert main.home() == {"message": "Crypto Price Prediction API Running"}
    assert main.health() == {"status": "ok"}


def test_symbol_helpers_and_news_fallback():
    assert main._symbol_to_coin_id("BTC-USD") == "bitcoin"
    assert main._symbol_to_coin_id("unknown") == "bitcoin"
    assert main._symbol_code("eth-usd") == "ETH"
    assert main._news_items_for_coin("ethereum")[0]["title"]
    assert main._news_items_for_coin("does-not-exist") == main.NEWS_FALLBACK["bitcoin"]


def test_fetch_google_news_rss_success_and_unavailable(monkeypatch):
    rss = b"""
    <rss><channel>
      <item><title>Bitcoin rallies</title><link>https://a</link><description><![CDATA[<b>Strong gain</b>]]></description><source>CoinDesk</source></item>
      <item><title></title><link>https://b</link></item>
    </channel></rss>
    """

    monkeypatch.setattr(main, "urlopen", lambda req, timeout=10: DummyResponse(rss))
    items, source = main._fetch_google_news_rss("bitcoin", "BTC", limit=5)
    assert source == "google-news-rss"
    assert len(items) == 1
    assert items[0]["summary"].strip() == "Strong gain"

    monkeypatch.setattr(main, "urlopen", lambda req, timeout=10: (_ for _ in ()).throw(RuntimeError("no net")))
    items, source = main._fetch_google_news_rss("bitcoin", "BTC", limit=5)
    assert items == []
    assert source == "unavailable"


def test_analyze_and_aggregate_sentiment_paths():
    assert main._analyze_text_sentiment("")["label"] == "neutral"
    assert main._analyze_text_sentiment("Bullish surge and breakout")["label"] == "positive"
    assert main._analyze_text_sentiment("Bearish crash and fear")["label"] == "negative"
    assert main._analyze_text_sentiment("bitcoin market sideways")["label"] == "neutral"

    assert main._aggregate_sentiment([]) == {"score": 0.0, "label": "neutral", "count": 0}
    assert main._aggregate_sentiment([{"sentiment_score": 0.8}, {"sentiment_score": 0.2}])["label"] == "positive"
    assert main._aggregate_sentiment([{"sentiment_score": -0.8}, {"sentiment_score": -0.2}])["label"] == "negative"
    assert main._aggregate_sentiment([{"sentiment_score": 0.0}, {"sentiment_score": 0.05}])["label"] == "neutral"


def test_extract_nitter_rss_tweets_success_then_fail(monkeypatch):
    call_count = {"value": 0}
    rss = b"""
    <rss><channel>
      <item><title>BTC is strong</title><link>https://x/status/1</link><pubDate>today</pubDate></item>
      <item><title></title><link>https://x/status/2</link></item>
    </channel></rss>
    """

    def fake_urlopen(req, timeout=10):
        call_count["value"] += 1
        if call_count["value"] == 1:
            raise RuntimeError("first endpoint down")
        return DummyResponse(rss)

    monkeypatch.setattr(main, "urlopen", fake_urlopen)
    tweets, source = main._extract_nitter_rss_tweets("BTC", limit=5)
    assert source == "twitter-rss"
    assert len(tweets) == 1

    monkeypatch.setattr(main, "urlopen", lambda req, timeout=10: (_ for _ in ()).throw(RuntimeError("all down")))
    tweets, source = main._extract_nitter_rss_tweets("BTC", limit=5)
    assert tweets == []
    assert source == "unavailable"


def test_extract_x_api_tweets_token_missing_success_and_failure(monkeypatch):
    monkeypatch.delenv("TWITTER_BEARER_TOKEN", raising=False)
    tweets, source = main._extract_x_api_tweets("BTC", limit=3)
    assert tweets == []
    assert source == "token-missing"

    payload = json.dumps(
        {
            "data": [
                {"id": "1", "text": "BTC uptrend", "created_at": "2026-01-01T00:00:00Z"},
                {"id": "2", "text": "   ", "created_at": "2026-01-01T00:00:00Z"},
            ]
        }
    ).encode("utf-8")
    monkeypatch.setenv("TWITTER_BEARER_TOKEN", "token")
    monkeypatch.setattr(main, "urlopen", lambda req, timeout=10: DummyResponse(payload))
    tweets, source = main._extract_x_api_tweets("BTC", limit=3)
    assert source == "twitter-api"
    assert len(tweets) == 1
    assert tweets[0]["url"].endswith("/1")

    monkeypatch.setattr(main, "urlopen", lambda req, timeout=10: (_ for _ in ()).throw(RuntimeError("api down")))
    tweets, source = main._extract_x_api_tweets("BTC", limit=3)
    assert tweets == []
    assert source == "twitter-api-failed"


def test_parse_iso_datetime_and_send_window(monkeypatch):
    assert main._parse_iso_datetime(None) is None
    assert main._parse_iso_datetime("bad") is None

    naive = main._parse_iso_datetime("2026-01-01T00:00:00")
    assert naive is not None
    assert naive.tzinfo is not None

    aware = main._parse_iso_datetime("2026-01-01T00:00:00Z")
    assert aware is not None
    assert aware.tzinfo == timezone.utc

    monkeypatch.setattr(main, "ALERT_EMAIL_INTERVAL_SECONDS", 3600)
    assert main._should_send_alert_email(None)

    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    recent_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    assert main._should_send_alert_email(old_time)
    assert not main._should_send_alert_email(recent_time)


def test_get_symbol_sentiment_label_paths(monkeypatch):
    monkeypatch.setattr(main, "_fetch_google_news_rss", lambda coin_id, code, limit=8: ([], "unavailable"))
    monkeypatch.setattr(main, "_news_items_for_coin", lambda coin: [])
    monkeypatch.setattr(main, "_extract_x_api_tweets", lambda query, limit=8: ([], "token-missing"))
    monkeypatch.setattr(main, "_extract_nitter_rss_tweets", lambda query, limit=8: ([], "unavailable"))
    assert main._get_symbol_sentiment_label("BTC-USD") is None

    monkeypatch.setattr(
        main,
        "_news_items_for_coin",
        lambda coin: [{"title": "bullish breakout", "summary": "strong momentum"}],
    )
    monkeypatch.setattr(
        main,
        "_extract_nitter_rss_tweets",
        lambda query, limit=8: ([{"text": "bearish crash"}], "twitter-rss"),
    )
    assert main._get_symbol_sentiment_label("BTC-USD") == "neutral"


def test_get_symbol_sentiment_label_positive_and_negative(monkeypatch):
    monkeypatch.setattr(
        main,
        "_fetch_google_news_rss",
        lambda coin_id, code, limit=8: ([{"title": "bullish breakout", "summary": "strong gain"}], "google-news-rss"),
    )
    monkeypatch.setattr(main, "_extract_x_api_tweets", lambda query, limit=8: ([{"text": "uptrend rally"}], "twitter-api"))
    assert main._get_symbol_sentiment_label("BTC-USD") == "positive"

    monkeypatch.setattr(
        main,
        "_fetch_google_news_rss",
        lambda coin_id, code, limit=8: ([{"title": "bearish crash", "summary": "risk grows"}], "google-news-rss"),
    )
    monkeypatch.setattr(main, "_extract_x_api_tweets", lambda query, limit=8: ([{"text": "falling market fear"}], "twitter-api"))
    assert main._get_symbol_sentiment_label("BTC-USD") == "negative"


def test_send_emailjs_alert_paths(monkeypatch):
    alert = {
        "symbol": "BTC-USD",
        "alert_type": "target",
        "direction": "above",
        "threshold_value": 60000,
        "sentiment_label": None,
        "latest_price": 60500,
        "pct_change_24h": 1.2,
        "reason": "target crossed",
    }

    monkeypatch.delenv("EMAILJS_SERVICE_ID", raising=False)
    monkeypatch.delenv("EMAILJS_TEMPLATE_ID", raising=False)
    monkeypatch.delenv("EMAILJS_PUBLIC_KEY", raising=False)
    ok, msg = main._send_emailjs_alert(alert, "user@example.com")
    assert not ok
    assert "not configured" in msg.lower()

    monkeypatch.setenv("EMAILJS_SERVICE_ID", "svc")
    monkeypatch.setenv("EMAILJS_TEMPLATE_ID", "tpl")
    monkeypatch.setenv("EMAILJS_PUBLIC_KEY", "pub")
    monkeypatch.setenv("EMAILJS_PRIVATE_KEY", "priv")

    monkeypatch.setattr(main, "urlopen", lambda req, timeout=15: DummyResponse(b"ok", status=200))
    ok, msg = main._send_emailjs_alert(alert, "user@example.com")
    assert ok and msg == "sent"

    monkeypatch.setattr(main, "urlopen", lambda req, timeout=15: DummyResponse(b"bad", status=500))
    ok, msg = main._send_emailjs_alert(alert, "user@example.com")
    assert not ok
    assert "http 500" in msg.lower()

    def raise_http_error(req, timeout=15):
        raise HTTPError(url="https://x", code=401, msg="Unauthorized", hdrs=None, fp=io.BytesIO(b"bad auth"))

    monkeypatch.setattr(main, "urlopen", raise_http_error)
    ok, msg = main._send_emailjs_alert(alert, "user@example.com")
    assert not ok
    assert "http error 401" in msg.lower()

    class BrokenBodyHttpError(HTTPError):
        def read(self):
            raise RuntimeError("cannot-read")

    def raise_http_error_without_body(req, timeout=15):
        raise BrokenBodyHttpError(url="https://x", code=500, msg="Server Error", hdrs=None, fp=None)

    monkeypatch.setattr(main, "urlopen", raise_http_error_without_body)
    ok, msg = main._send_emailjs_alert(alert, "user@example.com")
    assert not ok
    assert "http error 500" in msg.lower()

    monkeypatch.setattr(main, "urlopen", lambda req, timeout=15: (_ for _ in ()).throw(RuntimeError("boom")))
    ok, msg = main._send_emailjs_alert(alert, "user@example.com")
    assert not ok
    assert "boom" in msg


def test_run_alert_email_cycle_paths(monkeypatch):
    alerts = [
        {
            "id": 1,
            "user_id": 11,
            "symbol": "BTC-USD",
            "alert_type": "target",
            "threshold_value": 100,
            "direction": "above",
            "sentiment_label": None,
            "last_notified_at": None,
            "email": "a@example.com",
        },
        {
            "id": 2,
            "user_id": 11,
            "symbol": "BTC-USD",
            "alert_type": "sentiment",
            "threshold_value": None,
            "direction": "above",
            "sentiment_label": "positive",
            "last_notified_at": None,
            "email": "a@example.com",
        },
        {
            "id": 3,
            "user_id": 12,
            "symbol": "ETH-USD",
            "alert_type": "target",
            "threshold_value": 100,
            "direction": "above",
            "sentiment_label": None,
            "last_notified_at": None,
            "email": "b@example.com",
        },
    ]

    query_conn = DummyConn(rows=alerts)
    update_conn = DummyConn()
    conns = [query_conn, update_conn]

    monkeypatch.setattr(main, "get_connection", lambda: conns.pop(0))

    price_calls = {"count": 0}

    def fake_price(symbol):
        price_calls["count"] += 1
        return 100.0, 2.5

    monkeypatch.setattr(auth, "get_latest_price_and_change", fake_price)

    monkeypatch.setattr(main, "_get_symbol_sentiment_label", lambda symbol: "positive")

    def fake_eval(alert, latest_price=None, pct_change_24h=None, sentiment_label=None):
        if alert["id"] == 3:
            return {"is_triggered": False, "reason": "not reached", "latest_price": latest_price, "pct_change_24h": pct_change_24h}
        return {"is_triggered": True, "reason": "triggered", "latest_price": latest_price, "pct_change_24h": pct_change_24h}

    monkeypatch.setattr(main, "evaluate_alert_condition", fake_eval)
    monkeypatch.setattr(main, "_should_send_alert_email", lambda last_notified_at: True)

    sent_ids = []

    def fake_send(alert, recipient_email):
        sent_ids.append(alert["id"])
        if alert["id"] == 1:
            return False, "delivery failed"
        return True, "sent"

    monkeypatch.setattr(main, "_send_emailjs_alert", fake_send)

    usage_calls = []
    activity_calls = []
    monkeypatch.setattr(main, "track_api_usage", lambda provider, endpoint, user_id: usage_calls.append((provider, endpoint, user_id)))
    monkeypatch.setattr(main, "track_activity", lambda user_id, action, details="": activity_calls.append((user_id, action, details)))
    monkeypatch.setattr(main, "now_utc", lambda: "2026-01-01T00:00:00+00:00")

    main._run_alert_email_cycle()

    assert price_calls["count"] == 2
    assert sent_ids == [1, 2]
    assert usage_calls == [("emailjs", "alert_email", 11)]
    assert len(activity_calls) == 1
    assert any("UPDATE alerts SET last_notified_at" in sql for sql, _ in update_conn.executed)


def test_run_alert_email_cycle_with_no_alerts(monkeypatch):
    query_conn = DummyConn(rows=[])
    monkeypatch.setattr(main, "get_connection", lambda: query_conn)
    main._run_alert_email_cycle()
    assert query_conn.closed


@pytest.mark.anyio
async def test_alert_email_worker_cancelled(monkeypatch):
    async def fake_to_thread(fn):
        raise asyncio.CancelledError()

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    with pytest.raises(asyncio.CancelledError):
        await main._alert_email_worker()


@pytest.mark.anyio
async def test_alert_email_worker_logs_and_exits_on_sleep_cancel(monkeypatch):
    logged = {"called": False}

    async def fake_to_thread(fn):
        raise RuntimeError("worker failed")

    async def fake_sleep(seconds):
        raise asyncio.CancelledError()

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(main.logger, "exception", lambda *args, **kwargs: logged.__setitem__("called", True))

    with pytest.raises(asyncio.CancelledError):
        await main._alert_email_worker()
    assert logged["called"]


@pytest.mark.anyio
async def test_lifespan_starts_and_stops_worker(monkeypatch):
    class DummyTask:
        def __init__(self):
            self.cancel_called = False

        def cancel(self):
            self.cancel_called = True

        def __await__(self):
            async def _done():
                return None

            return _done().__await__()

    dummy_task = DummyTask()
    def fake_create_task(coro):
        coro.close()
        return dummy_task

    monkeypatch.setattr(asyncio, "create_task", fake_create_task)

    async with main.lifespan(main.app):
        assert main.app.state.alert_email_task is dummy_task

    assert dummy_task.cancel_called
    assert main.app.state.alert_email_task is None


def test_coin_news_route_live_and_fallback(monkeypatch):
    monkeypatch.setattr(main, "_fetch_google_news_rss", lambda coin_id, code, limit=8: ([{"title": "Live", "url": "https://a"}], "google-news-rss"))
    assert main.get_coin_news("BTC", current_user={})[0]["title"] == "Live"

    monkeypatch.setattr(main, "_fetch_google_news_rss", lambda coin_id, code, limit=8: ([], "unavailable"))
    out = main.get_coin_news("BTC", current_user={})
    assert out == main.NEWS_FALLBACK["bitcoin"]


def test_sentiment_summary_route_paths(monkeypatch):
    monkeypatch.delenv("TWITTER_BEARER_TOKEN", raising=False)
    monkeypatch.setattr(main, "_fetch_google_news_rss", lambda coin_id, code, limit=10: ([], "unavailable"))
    monkeypatch.setattr(main, "_news_items_for_coin", lambda coin: [{"title": "bullish rally", "summary": "strong gain", "url": "https://n", "source": "curated"}])
    monkeypatch.setattr(main, "_extract_x_api_tweets", lambda query, limit=10: ([], "token-missing"))
    monkeypatch.setattr(main, "_extract_nitter_rss_tweets", lambda query, limit=10: ([{"text": "bearish risk", "url": "https://t", "created_at": "today", "source": "twitter-rss"}], "twitter-rss"))

    result = main.get_sentiment_summary("BTC-USD", limit=50, current_user={})
    assert result["news"]["source"] == "curated-fallback"
    assert result["twitter"]["source"] == "twitter-rss"
    assert result["twitter"]["is_configured"] is False
    assert result["overall"]["label"] in {"neutral", "positive", "negative"}

    monkeypatch.setenv("TWITTER_BEARER_TOKEN", "token")
    monkeypatch.setattr(main, "_fetch_google_news_rss", lambda coin_id, code, limit=10: ([], "unavailable"))
    monkeypatch.setattr(main, "_news_items_for_coin", lambda coin: [])
    monkeypatch.setattr(main, "_extract_x_api_tweets", lambda query, limit=10: ([], "twitter-api"))
    monkeypatch.setattr(main, "_extract_nitter_rss_tweets", lambda query, limit=10: ([], "unavailable"))

    result = main.get_sentiment_summary("BTC-USD", limit=1, current_user={})
    assert result["twitter"]["is_configured"] is True
    assert result["overall"] == {"label": "neutral", "score": 0.0}


def test_sentiment_summary_positive_and_negative_overall(monkeypatch):
    monkeypatch.setattr(
        main,
        "_fetch_google_news_rss",
        lambda coin_id, code, limit=10: ([{"title": "bullish rally", "summary": "strong gains", "url": "https://n", "source": "news"}], "google-news-rss"),
    )
    monkeypatch.setattr(main, "_extract_x_api_tweets", lambda query, limit=10: ([{"text": "uptrend breakout", "url": "https://t", "created_at": "now", "source": "twitter-api"}], "twitter-api"))
    positive = main.get_sentiment_summary("BTC-USD", limit=10, current_user={})
    assert positive["overall"]["label"] == "positive"

    monkeypatch.setattr(
        main,
        "_fetch_google_news_rss",
        lambda coin_id, code, limit=10: ([{"title": "bearish crash", "summary": "deep losses", "url": "https://n", "source": "news"}], "google-news-rss"),
    )
    monkeypatch.setattr(main, "_extract_x_api_tweets", lambda query, limit=10: ([{"text": "downtrend fear", "url": "https://t", "created_at": "now", "source": "twitter-api"}], "twitter-api"))
    negative = main.get_sentiment_summary("BTC-USD", limit=10, current_user={})
    assert negative["overall"]["label"] == "negative"


def test_live_market_coingecko_and_fallback(monkeypatch):
    chart_payload = json.dumps({"prices": [[1700000000000, 100.0], [1700003600000, 101.0]]}).encode("utf-8")
    price_payload = json.dumps({"bitcoin": {"usd": 102.5}}).encode("utf-8")

    calls = {"n": 0}

    def fake_urlopen(req, timeout=12):
        calls["n"] += 1
        if calls["n"] == 1:
            return DummyResponse(chart_payload)
        return DummyResponse(price_payload)

    monkeypatch.setattr(main, "urlopen", fake_urlopen)
    out = main.get_live_market(symbol="BTC-USD", days=100, current_user={})
    assert out["source"] == "coingecko"
    assert out["days"] == 30
    assert out["current_price"] == 102.5
    assert len(out["prices"]) == 2

    monkeypatch.setattr(main, "urlopen", lambda req, timeout=12: (_ for _ in ()).throw(RuntimeError("coingecko down")))

    idx = pd.to_datetime(["2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"])
    df = pd.DataFrame({"Close": [200.0, 201.0]}, index=idx)
    monkeypatch.setattr(main.yf, "download", lambda *args, **kwargs: df)

    out = main.get_live_market(symbol="BTC-USD", days=0, current_user={})
    assert out["source"] == "yfinance"
    assert out["days"] == 1
    assert out["current_price"] == 201.0


def test_live_market_coingecko_current_price_from_points(monkeypatch):
    chart_payload = json.dumps({"prices": [[1700000000000, 100.0], [1700003600000, 101.0]]}).encode("utf-8")
    price_payload = json.dumps({"bitcoin": {}}).encode("utf-8")

    calls = {"n": 0}

    def fake_urlopen(req, timeout=12):
        calls["n"] += 1
        return DummyResponse(chart_payload if calls["n"] == 1 else price_payload)

    monkeypatch.setattr(main, "urlopen", fake_urlopen)
    out = main.get_live_market(symbol="BTC-USD", days=1, current_user={})
    assert out["source"] == "coingecko"
    assert out["current_price"] == 101.0


def test_live_market_fallback_edge_cases(monkeypatch):
    monkeypatch.setattr(main, "urlopen", lambda req, timeout=12: DummyResponse(json.dumps({"prices": []}).encode("utf-8")))

    idx = pd.to_datetime(["2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"])
    multi_df = pd.DataFrame(
        {
            ("Close", "BTC-USD"): [200.0, 201.0],
            ("Open", "BTC-USD"): [190.0, 195.0],
        },
        index=idx,
    )
    monkeypatch.setattr(main.yf, "download", lambda *args, **kwargs: multi_df)
    out = main.get_live_market(symbol="BTC-USD", days=5, current_user={})
    assert out["source"] == "yfinance"

    no_close_df = pd.DataFrame({"Open": [1.0, 2.0]}, index=idx)
    monkeypatch.setattr(main.yf, "download", lambda *args, **kwargs: no_close_df)
    with pytest.raises(main.HTTPException) as exc:
        main.get_live_market(symbol="BTC-USD", days=5, current_user={})
    assert exc.value.status_code == 502

    all_nan_df = pd.DataFrame({"Close": [None, None]}, index=idx)
    monkeypatch.setattr(main.yf, "download", lambda *args, **kwargs: all_nan_df)
    with pytest.raises(main.HTTPException) as exc:
        main.get_live_market(symbol="BTC-USD", days=5, current_user={})
    assert exc.value.status_code == 502


def test_live_market_raises_when_all_upstreams_fail(monkeypatch):
    monkeypatch.setattr(main, "urlopen", lambda req, timeout=12: (_ for _ in ()).throw(RuntimeError("coingecko down")))
    monkeypatch.setattr(main.yf, "download", lambda *args, **kwargs: pd.DataFrame())

    with pytest.raises(main.HTTPException) as exc:
        main.get_live_market(symbol="BTC-USD", days=1, current_user={})
    assert exc.value.status_code == 502
