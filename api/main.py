# api/main.py
import sys
import os
import json
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
    normalized = (coin or "Bitcoin").strip().lower()
    if normalized in NEWS_FALLBACK:
        return NEWS_FALLBACK[normalized]
    return NEWS_FALLBACK["bitcoin"]


def _symbol_to_coin_id(symbol: str) -> str:
    key = (symbol or "BTC-USD").upper().replace("-USD", "").strip()
    return COIN_SYMBOL_MAP.get(key, "bitcoin")


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

