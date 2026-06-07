import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd

COIN_SYMBOL_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "XRP": "ripple",
    "BNB": "binancecoin",
    "LTC": "litecoin",
    "DOT": "polkadot",
}

NEWS_FALLBACK = {
    "bitcoin": [
        {"title": "Bitcoin market update", "url": "https://www.coindesk.com/", "source": "CoinDesk"},
        {"title": "Latest Bitcoin analysis", "url": "https://cointelegraph.com/tags/bitcoin", "source": "Cointelegraph"},
    ],
    "ethereum": [
        {"title": "Ethereum ecosystem update", "url": "https://www.coindesk.com/tag/ethereum/", "source": "CoinDesk"},
        {"title": "Latest Ethereum analysis", "url": "https://cointelegraph.com/tags/ethereum", "source": "Cointelegraph"},
    ],
    "solana": [
        {"title": "Solana ecosystem update", "url": "https://cointelegraph.com/tags/solana", "source": "Cointelegraph"}
    ],
    "cardano": [
        {"title": "Cardano ecosystem update", "url": "https://cointelegraph.com/tags/cardano", "source": "Cointelegraph"}
    ],
}

SYMBOL_KEYWORDS = {
    "BTC": ["bitcoin", "btc", "#btc"],
    "ETH": ["ethereum", "eth", "#eth"],
    "SOL": ["solana", "sol", "#sol"],
    "ADA": ["cardano", "ada", "#ada"],
    "XRP": ["xrp", "ripple", "#xrp"],
    "DOGE": ["dogecoin", "doge", "#doge"],
    "BNB": ["bnb", "binance", "#bnb"],
    "LTC": ["litecoin", "ltc", "#ltc"],
    "DOT": ["polkadot", "dot", "#dot"],
}

POSITIVE_WORDS = {
    "bullish", "uptrend", "breakout", "rally", "gain", "gains", "growth", "surge", "pump",
    "strong", "support", "accumulation", "adoption", "buy", "bought", "higher", "positive",
    "recover", "recovery", "green", "momentum", "confidence", "optimistic",
}

NEGATIVE_WORDS = {
    "bearish", "downtrend", "breakdown", "drop", "loss", "losses", "weak", "sell", "sold",
    "panic", "crash", "dump", "fear", "liquidation", "resistance", "lower", "negative",
    "red", "risk", "uncertain", "volatility", "volatile", "decline", "fall",
}

EMAILJS_SEND_URL = "https://api.emailjs.com/api/v1.0/email/send"


def symbol_to_coin_id(symbol: str) -> str:
    key = (symbol or "BTC-USD").upper().replace("-USD", "").strip()
    return COIN_SYMBOL_MAP.get(key, "bitcoin")


def symbol_code(symbol: str) -> str:
    return (symbol or "BTC-USD").upper().replace("-USD", "").strip()


def news_items_for_coin(coin: str):
    normalized = (coin or "bitcoin").strip().lower()
    return NEWS_FALLBACK.get(normalized, NEWS_FALLBACK["bitcoin"])


def fetch_google_news_rss(coin_id: str, code: str, limit: int = 10) -> tuple[list[dict], str]:
    query = quote(f"{coin_id} OR {code} crypto")
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    req_headers = {"User-Agent": "crypto-price-prediction/1.0"}
    try:
        with urlopen(Request(rss_url, headers=req_headers), timeout=10) as resp:
            payload = resp.read()
        root = ET.fromstring(payload)
        out = []
        for item in root.findall("./channel/item")[:limit]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()
            src = (item.findtext("source") or "Google News").strip()
            if not title:
                continue
            out.append({"title": title, "summary": re.sub(r"<[^>]+>", " ", desc), "url": link, "source": src})
        return out, "google-news-rss"
    except Exception:
        return [], "unavailable"


def analyze_text_sentiment(text: str) -> dict:
    cleaned = re.sub(r"[^a-zA-Z#\s]", " ", (text or "").lower())
    tokens = [token for token in cleaned.split() if token]
    if not tokens:
        return {"score": 0.0, "label": "neutral", "positive_hits": 0, "negative_hits": 0}

    positive_roots = ("bull", "gain", "surge", "rise", "up", "recover", "breakout", "optim")
    negative_roots = ("bear", "loss", "drop", "fall", "down", "crash", "risk", "volatil", "fear")

    pos_hits = sum(1 for token in tokens if (token in POSITIVE_WORDS or token.startswith(positive_roots)))
    neg_hits = sum(1 for token in tokens if (token in NEGATIVE_WORDS or token.startswith(negative_roots)))
    score = (pos_hits - neg_hits) / max(len(tokens), 8)
    score = max(-1.0, min(1.0, score * 4.0))

    if score > 0.12:
        label = "positive"
    elif score < -0.12:
        label = "negative"
    else:
        label = "neutral"

    return {"score": float(score), "label": label, "positive_hits": int(pos_hits), "negative_hits": int(neg_hits)}


def aggregate_sentiment(items: list[dict]) -> dict:
    if not items:
        return {"score": 0.0, "label": "neutral", "count": 0}
    avg_score = float(sum(item.get("sentiment_score", 0.0) for item in items) / len(items))
    if avg_score > 0.12:
        label = "positive"
    elif avg_score < -0.12:
        label = "negative"
    else:
        label = "neutral"
    return {"score": avg_score, "label": label, "count": len(items)}


def extract_nitter_rss_tweets(query: str, limit: int = 10) -> tuple[list[dict], str]:
    encoded = quote(query)
    candidates = [
        f"https://nitter.net/search/rss?f=tweets&q={encoded}",
        f"https://nitter.poast.org/search/rss?f=tweets&q={encoded}",
        f"https://nitter.privacyredirect.com/search/rss?f=tweets&q={encoded}",
    ]
    req_headers = {"User-Agent": "crypto-price-prediction/1.0"}
    for url in candidates:
        try:
            with urlopen(Request(url, headers=req_headers), timeout=10) as resp:
                payload = resp.read()
            root = ET.fromstring(payload)
            out = []
            for item in root.findall("./channel/item")[:limit]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                if not title:
                    continue
                out.append({"text": title, "url": link, "created_at": pub_date, "source": "twitter-rss"})
            if out:
                return out, "twitter-rss"
        except Exception:
            continue
    return [], "unavailable"


def extract_x_api_tweets(query: str, limit: int = 10) -> tuple[list[dict], str]:
    bearer = (os.getenv("TWITTER_BEARER_TOKEN") or "").strip()
    if not bearer:
        return [], "token-missing"
    search_url = (
        "https://api.twitter.com/2/tweets/search/recent"
        f"?query={quote(query)}&max_results={max(10, min(limit, 50))}"
        "&tweet.fields=created_at,lang"
    )
    req_headers = {"User-Agent": "crypto-price-prediction/1.0", "Authorization": f"Bearer {bearer}"}
    try:
        with urlopen(Request(search_url, headers=req_headers), timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        tweets = []
        for row in data.get("data", [])[:limit]:
            text = (row.get("text") or "").strip()
            if not text:
                continue
            tweets.append({
                "text": text,
                "url": "https://twitter.com/i/web/status/" + str(row.get("id", "")),
                "created_at": row.get("created_at"),
                "source": "twitter-api",
            })
        return tweets, "twitter-api"
    except Exception:
        return [], "twitter-api-failed"


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def should_send_alert_email(last_notified_at: str | None, interval_seconds: int) -> bool:
    last_sent = parse_iso_datetime(last_notified_at)
    if last_sent is None:
        return True
    elapsed = datetime.now(timezone.utc) - last_sent
    return elapsed.total_seconds() >= interval_seconds


def get_symbol_sentiment_label(
    symbol: str,
    fetch_google_news_rss: Callable[[str, str, int], tuple[list[dict], str]],
    news_items_for_coin: Callable[[str], list[dict]],
    analyze_text_sentiment: Callable[[str], dict],
    aggregate_sentiment: Callable[[list[dict]], dict],
    extract_x_api_tweets: Callable[[str, int], tuple[list[dict], str]],
    extract_nitter_rss_tweets: Callable[[str, int], tuple[list[dict], str]],
) -> str | None:
    coin_id = symbol_to_coin_id(symbol)
    code = symbol_code(symbol)

    news_raw, _ = fetch_google_news_rss(coin_id, code, limit=8)
    if not news_raw:
        news_raw = news_items_for_coin(coin_id)
    news_scores = []
    for item in news_raw[:8]:
        analyzed = analyze_text_sentiment(f"{item.get('title', '')} {item.get('summary', '')}")
        news_scores.append({"sentiment_score": analyzed["score"]})

    keyword = " OR ".join(SYMBOL_KEYWORDS.get(code, [code.lower()])) + " lang:en"
    tweets, _ = extract_x_api_tweets(keyword, limit=8)
    if not tweets:
        tweets, _ = extract_nitter_rss_tweets(f"{code} OR {coin_id} lang:en", limit=8)
    tweet_scores = []
    for item in tweets[:8]:
        analyzed = analyze_text_sentiment(item.get("text", ""))
        tweet_scores.append({"sentiment_score": analyzed["score"]})

    summaries = []
    if news_scores:
        summaries.append(aggregate_sentiment(news_scores))
    if tweet_scores:
        summaries.append(aggregate_sentiment(tweet_scores))
    if not summaries:
        return None

    overall_score = sum(item["score"] for item in summaries) / len(summaries)
    if overall_score > 0.12:
        return "positive"
    if overall_score < -0.12:
        return "negative"
    return "neutral"


def send_emailjs_alert(alert: dict, recipient_email: str, now_utc: Callable[[], str]) -> tuple[bool, str]:
    service_id = (os.getenv("EMAILJS_SERVICE_ID") or "").strip()
    template_id = (os.getenv("EMAILJS_TEMPLATE_ID") or "").strip()
    public_key = (os.getenv("EMAILJS_PUBLIC_KEY") or "").strip()
    private_key = (os.getenv("EMAILJS_PRIVATE_KEY") or "").strip()

    if not service_id or not template_id or not public_key:
        return False, "EmailJS is not configured."

    payload = {
        "service_id": service_id,
        "template_id": template_id,
        "user_id": public_key,
        "template_params": {
            "to_email": recipient_email,
            "user_email": recipient_email,
            "symbol": alert["symbol"],
            "alert_type": alert["alert_type"],
            "direction": alert.get("direction") or "",
            "threshold_value": "" if alert.get("threshold_value") is None else str(alert.get("threshold_value")),
            "sentiment_label": alert.get("sentiment_label") or "",
            "latest_price": "" if alert.get("latest_price") is None else f"{float(alert['latest_price']):.2f}",
            "pct_change_24h": "" if alert.get("pct_change_24h") is None else f"{float(alert['pct_change_24h']):.2f}",
            "reason": alert.get("reason") or "Alert condition triggered.",
            "triggered_at": now_utc(),
        },
    }
    if private_key:
        payload["accessToken"] = private_key

    req = Request(
        EMAILJS_SEND_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://dashboard.emailjs.com",
            "Referer": "https://dashboard.emailjs.com/",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=15) as resp:
            status = getattr(resp, "status", 200)
            if status >= 400:
                return False, f"EmailJS returned HTTP {status}."
        return True, "sent"
    except HTTPError as exc:
        try:
            error_body = exc.read().decode("utf-8", errors="replace").strip()
        except Exception:
            error_body = ""
        detail = f"HTTP Error {exc.code}: {exc.reason}"
        if error_body:
            detail = f"{detail} | {error_body}"
        return False, detail
    except Exception as exc:
        return False, str(exc)


def run_alert_email_cycle(
    get_connection: Callable[[], Any],
    get_latest_price_and_change: Callable[[str], tuple[Optional[float], Optional[float]]],
    get_symbol_sentiment_label: Callable[[str], str | None],
    evaluate_alert_condition: Callable[..., dict],
    should_send_alert_email: Callable[[str | None], bool],
    send_emailjs_alert: Callable[[dict, str], tuple[bool, str]],
    track_api_usage: Callable[[str, str, Optional[int]], None],
    track_activity: Callable[[Optional[int], str, str], None],
    now_utc: Callable[[], str],
    logger: Any,
) -> None:
    conn = get_connection()
    try:
        alerts = conn.execute(
            """
            SELECT a.id, a.user_id, a.symbol, a.alert_type, a.threshold_value, a.direction,
                   a.sentiment_label, a.last_notified_at, u.email
            FROM alerts a
            JOIN users u ON u.id = a.user_id
            WHERE a.is_enabled = 1 AND a.email_enabled = 1 AND u.status = 'approved'
            ORDER BY a.id ASC
            """
        ).fetchall()
    finally:
        conn.close()

    if not alerts:
        return

    live_cache: dict[str, tuple[float | None, float | None]] = {}
    sentiment_cache: dict[str, str | None] = {}

    for row in alerts:
        alert = dict(row)
        symbol = alert["symbol"]

        if symbol not in live_cache:
            live_cache[symbol] = get_latest_price_and_change(symbol)

        latest_price, pct_change_24h = live_cache[symbol]
        sentiment_label = None
        if alert["alert_type"] == "sentiment":
            if symbol not in sentiment_cache:
                sentiment_cache[symbol] = get_symbol_sentiment_label(symbol)
            sentiment_label = sentiment_cache[symbol]

        evaluation = evaluate_alert_condition(
            alert,
            latest_price=latest_price,
            pct_change_24h=pct_change_24h,
            sentiment_label=sentiment_label,
        )
        if not evaluation["is_triggered"] or not should_send_alert_email(alert.get("last_notified_at")):
            continue

        delivered, status_message = send_emailjs_alert({**alert, **evaluation}, recipient_email=alert["email"])
        if not delivered:
            logger.warning("Alert email delivery failed for alert_id=%s: %s", alert["id"], status_message)
            continue

        track_api_usage("emailjs", "alert_email", alert["user_id"])
        track_activity(alert["user_id"], "user.alert.email_sent", f"alert_id={alert['id']}, symbol={symbol}")

        update_conn = get_connection()
        try:
            update_conn.execute("UPDATE alerts SET last_notified_at = ? WHERE id = ?", (now_utc(), alert["id"]))
            update_conn.commit()
        finally:
            update_conn.close()


def get_live_market(symbol: str, days: int, yf_module: Any) -> dict:
    days = max(1, min(int(days), 30))
    coin_id = symbol_to_coin_id(symbol)

    try:
        chart_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}"
        price_url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        req_headers = {"User-Agent": "crypto-price-prediction/1.0"}
        with urlopen(Request(chart_url, headers=req_headers), timeout=12) as chart_resp:
            chart_data = json.loads(chart_resp.read().decode("utf-8"))
        with urlopen(Request(price_url, headers=req_headers), timeout=12) as price_resp:
            price_data = json.loads(price_resp.read().decode("utf-8"))

        points = [
            {"time": int(row[0]), "price": float(row[1])}
            for row in chart_data.get("prices", [])
            if isinstance(row, list) and len(row) >= 2
        ]
        current_price = price_data.get(coin_id, {}).get("usd")
        if current_price is None and points:
            current_price = points[-1]["price"]
        if not points:
            raise ValueError("No chart points returned from CoinGecko")
        return {
            "source": "coingecko",
            "symbol": symbol,
            "coin_id": coin_id,
            "days": days,
            "current_price": float(current_price) if current_price is not None else None,
            "prices": points,
        }
    except Exception:
        pass

    interval = "5m" if days <= 1 else ("1h" if days <= 7 else "1d")
    df = yf_module.download(symbol, period=f"{days}d", interval=interval, progress=False, auto_adjust=False)
    if df is None or df.empty:
        raise ValueError("No data returned from Yahoo Finance")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    close_col = "Close" if "Close" in df.columns else "close"
    if close_col not in df.columns:
        raise ValueError("Close column not present in Yahoo Finance response")

    close_series = df[close_col].dropna()
    points = [{"time": int(pd.Timestamp(ts).timestamp() * 1000), "price": float(px)} for ts, px in close_series.items()]
    if not points:
        raise ValueError("No chart points after processing Yahoo Finance data")

    return {
        "source": "yfinance",
        "symbol": symbol,
        "coin_id": coin_id,
        "days": days,
        "current_price": points[-1]["price"],
        "prices": points,
    }
