# api/main.py
import sys
import os
import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import quote
from urllib.request import Request, urlopen
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from api.auth import router as auth_router, require_role
import pandas as pd
import yfinance as yf

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
        {
            "title": "Bitcoin market update",
            "url": "https://www.coindesk.com/",
            "source": "CoinDesk",
        },
        {
            "title": "Latest Bitcoin analysis",
            "url": "https://cointelegraph.com/tags/bitcoin",
            "source": "Cointelegraph",
        },
    ],
    "ethereum": [
        {
            "title": "Ethereum ecosystem update",
            "url": "https://www.coindesk.com/tag/ethereum/",
            "source": "CoinDesk",
        },
        {
            "title": "Latest Ethereum analysis",
            "url": "https://cointelegraph.com/tags/ethereum",
            "source": "Cointelegraph",
        },
    ],
    "solana": [
        {
            "title": "Solana ecosystem update",
            "url": "https://cointelegraph.com/tags/solana",
            "source": "Cointelegraph",
        }
    ],
    "cardano": [
        {
            "title": "Cardano ecosystem update",
            "url": "https://cointelegraph.com/tags/cardano",
            "source": "Cointelegraph",
        }
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

app = FastAPI()
app.include_router(auth_router)

# Allow CORS for frontend (explicit whitelisted origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Crypto Price Prediction API Running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/coin-news")
def get_coin_news(
    coin: str = "Bitcoin",
    current_user=Depends(require_role("user", "researcher", "admin")),
):
    """Return lightweight curated news links for the requested coin."""
    code = (coin or "BTC").upper().replace("-USD", "").strip()
    coin_id = _symbol_to_coin_id(f"{code}-USD")
    live_items, _ = _fetch_google_news_rss(coin_id, code, limit=8)
    if live_items:
        return live_items
    return _news_items_for_coin(coin)


@app.get("/api/sentiment")
def get_sentiment_summary(
    symbol: str = "BTC-USD",
    limit: int = 10,
    current_user=Depends(require_role("user", "researcher", "admin")),
):
    """Aggregate sentiment from curated news and Twitter-like feeds (API/RSS fallback)."""
    limit = max(3, min(int(limit), 20))
    coin_id = _symbol_to_coin_id(symbol)
    code = _symbol_code(symbol)

    # News sentiment
    news_raw, news_source = _fetch_google_news_rss(coin_id, code, limit=limit)
    if not news_raw:
        news_raw = _news_items_for_coin(coin_id)
        news_source = "curated-fallback"
    news_items = []
    for n in news_raw[:limit]:
        base_text = f"{n.get('title', '')} {n.get('summary', '')}"
        s = _analyze_text_sentiment(base_text)
        news_items.append(
            {
                "title": n.get("title"),
                "source": n.get("source", "news"),
                "url": n.get("url"),
                "sentiment_label": s["label"],
                "sentiment_score": s["score"],
            }
        )
    news_summary = _aggregate_sentiment(news_items)

    # Twitter sentiment (official API first, RSS fallback)
    keyword = " OR ".join(SYMBOL_KEYWORDS.get(code, [code.lower()])) + " lang:en"
    tweets, twitter_source = _extract_x_api_tweets(keyword, limit=limit)
    if not tweets:
        rss_query = f"{code} OR {coin_id} lang:en"
        tweets, twitter_source = _extract_nitter_rss_tweets(rss_query, limit=limit)

    tweet_items = []
    for t in tweets[:limit]:
        s = _analyze_text_sentiment(t.get("text", ""))
        tweet_items.append(
            {
                "text": t.get("text"),
                "url": t.get("url"),
                "created_at": t.get("created_at"),
                "source": t.get("source", twitter_source),
                "sentiment_label": s["label"],
                "sentiment_score": s["score"],
            }
        )
    twitter_summary = _aggregate_sentiment(tweet_items)

    # Overall blend (news + twitter equally when both exist)
    blend_items = [i for i in [news_summary, twitter_summary] if i.get("count", 0) > 0]
    if blend_items:
        overall_score = float(sum(i["score"] for i in blend_items) / len(blend_items))
    else:
        overall_score = 0.0

    if overall_score > 0.12:
        overall_label = "positive"
    elif overall_score < -0.12:
        overall_label = "negative"
    else:
        overall_label = "neutral"

    return {
        "symbol": symbol,
        "coin_id": coin_id,
        "overall": {
            "label": overall_label,
            "score": overall_score,
        },
        "news": {
            "source": news_source,
            "summary": news_summary,
            "items": news_items,
        },
        "twitter": {
            "source": twitter_source,
            "summary": twitter_summary,
            "items": tweet_items,
            "is_configured": bool((os.getenv("TWITTER_BEARER_TOKEN") or "").strip()),
            "note": "Set TWITTER_BEARER_TOKEN for direct X API coverage. RSS fallback is used otherwise.",
        },
    }


def _symbol_to_coin_id(symbol: str) -> str:
    key = (symbol or "BTC-USD").upper().replace("-USD", "").strip()
    return COIN_SYMBOL_MAP.get(key, "bitcoin")


def _symbol_code(symbol: str) -> str:
    return (symbol or "BTC-USD").upper().replace("-USD", "").strip()


def _news_items_for_coin(coin: str):
    normalized = (coin or "bitcoin").strip().lower()
    return NEWS_FALLBACK.get(normalized, NEWS_FALLBACK["bitcoin"])


def _fetch_google_news_rss(coin_id: str, code: str, limit: int = 10) -> tuple[list[dict], str]:
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
            out.append(
                {
                    "title": title,
                    "summary": re.sub(r"<[^>]+>", " ", desc),
                    "url": link,
                    "source": src,
                }
            )
        return out, "google-news-rss"
    except Exception:
        return [], "unavailable"


def _analyze_text_sentiment(text: str) -> dict:
    cleaned = re.sub(r"[^a-zA-Z#\s]", " ", (text or "").lower())
    tokens = [t for t in cleaned.split() if t]
    if not tokens:
        return {"score": 0.0, "label": "neutral", "positive_hits": 0, "negative_hits": 0}

    positive_roots = ("bull", "gain", "surge", "rise", "up", "recover", "breakout", "optim")
    negative_roots = ("bear", "loss", "drop", "fall", "down", "crash", "risk", "volatil", "fear")

    pos_hits = sum(1 for t in tokens if (t in POSITIVE_WORDS or t.startswith(positive_roots)))
    neg_hits = sum(1 for t in tokens if (t in NEGATIVE_WORDS or t.startswith(negative_roots)))
    score = (pos_hits - neg_hits) / max(len(tokens), 8)
    score = max(-1.0, min(1.0, score * 4.0))

    if score > 0.12:
        label = "positive"
    elif score < -0.12:
        label = "negative"
    else:
        label = "neutral"

    return {
        "score": float(score),
        "label": label,
        "positive_hits": int(pos_hits),
        "negative_hits": int(neg_hits),
    }


def _aggregate_sentiment(items: list[dict]) -> dict:
    if not items:
        return {"score": 0.0, "label": "neutral", "count": 0}

    avg_score = float(sum(i.get("sentiment_score", 0.0) for i in items) / len(items))
    if avg_score > 0.12:
        label = "positive"
    elif avg_score < -0.12:
        label = "negative"
    else:
        label = "neutral"

    return {"score": avg_score, "label": label, "count": len(items)}


def _extract_nitter_rss_tweets(query: str, limit: int = 10) -> tuple[list[dict], str]:
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


def _extract_x_api_tweets(query: str, limit: int = 10) -> tuple[list[dict], str]:
    bearer = (os.getenv("TWITTER_BEARER_TOKEN") or "").strip()
    if not bearer:
        return [], "token-missing"

    search_url = (
        "https://api.twitter.com/2/tweets/search/recent"
        f"?query={quote(query)}&max_results={max(10, min(limit, 50))}"
        "&tweet.fields=created_at,lang"
    )
    req_headers = {
        "User-Agent": "crypto-price-prediction/1.0",
        "Authorization": f"Bearer {bearer}",
    }

    try:
        with urlopen(Request(search_url, headers=req_headers), timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        tweets = []
        for row in data.get("data", [])[:limit]:
            text = (row.get("text") or "").strip()
            if not text:
                continue
            tweets.append(
                {
                    "text": text,
                    "url": "https://twitter.com/i/web/status/" + str(row.get("id", "")),
                    "created_at": row.get("created_at"),
                    "source": "twitter-api",
                }
            )
        return tweets, "twitter-api"
    except Exception:
        return [], "twitter-api-failed"


@app.get("/api/live-market")
def get_live_market(
    symbol: str = "BTC-USD",
    days: int = 1,
    current_user=Depends(require_role("user", "researcher", "admin")),
):
    """Proxy live market data with CoinGecko primary and yfinance fallback."""
    days = max(1, min(int(days), 30))
    coin_id = _symbol_to_coin_id(symbol)

    # Primary source: CoinGecko
    try:
        chart_url = (
            f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
            f"?vs_currency=usd&days={days}"
        )
        price_url = (
            "https://api.coingecko.com/api/v3/simple/price"
            f"?ids={coin_id}&vs_currencies=usd"
        )

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

    # Fallback source: Yahoo Finance
    try:
        interval = "5m" if days <= 1 else ("1h" if days <= 7 else "1d")
        df = yf.download(
            symbol,
            period=f"{days}d",
            interval=interval,
            progress=False,
            auto_adjust=False,
        )

        if df is None or df.empty:
            raise ValueError("No data returned from Yahoo Finance")

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]

        close_col = "Close" if "Close" in df.columns else "close"
        if close_col not in df.columns:
            raise ValueError("Close column not present in Yahoo Finance response")

        close_series = df[close_col].dropna()
        points = [
            {
                "time": int(pd.Timestamp(ts).timestamp() * 1000),
                "price": float(px),
            }
            for ts, px in close_series.items()
        ]

        current_price = points[-1]["price"] if points else None

        if not points:
            raise ValueError("No chart points after processing Yahoo Finance data")

        return {
            "source": "yfinance",
            "symbol": symbol,
            "coin_id": coin_id,
            "days": days,
            "current_price": current_price,
            "prices": points,
        }
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Live market data is temporarily unavailable from upstream providers.",
        )

