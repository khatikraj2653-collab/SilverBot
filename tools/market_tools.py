import yfinance as yf
from langchain_core.tools import tool
from tools.cache_utils import cached_tool, TTL_GOLD_SILVER, TTL_RISK_SENTIMENT, TTL_USD_INDEX

yf.set_tz_cache_location("D:\\yf_cache")


def _last_close(symbol: str, period: str = "5d"):
    """Reliable last-close helper: yfinance .info is often None on cloud IPs
    (Yahoo rate-limits or returns empty JSON), so always prefer .history()."""
    try:
        hist = yf.Ticker(symbol).history(period=period, interval="1d")
        if hist is None or hist.empty:
            return None
        closes = hist["Close"].dropna()
        if closes.empty:
            return None
        return float(closes.iloc[-1])
    except Exception:
        return None


@tool
@cached_tool(TTL_GOLD_SILVER)
def get_gold_silver_ratio() -> str:
    """Fetches the current Gold-Silver Ratio (gold price / silver price) - a historically
    mean-reverting signal unique to silver; extreme ratios often predict silver catch-up rallies."""
    try:
        gold = _last_close("GC=F")
        silver = _last_close("SI=F")
        if gold is None or silver is None or silver == 0:
            return f"Gold-Silver Ratio: Data unavailable (Gold: {gold}, Silver: {silver})"
        ratio = round(gold / silver, 2)
        return f"Gold-Silver Ratio: {ratio} (Gold: ${round(gold,2)}, Silver: ${round(silver,2)})"
    except Exception as e:
        return f"Gold-Silver Ratio: Data unavailable ({str(e)})"


@tool
@cached_tool(TTL_RISK_SENTIMENT)
def get_risk_sentiment() -> str:
    """Fetches VIX and S&P 500 1-month growth combined into one 'Risk Sentiment' signal,
    both proxying risk-on/risk-off rotation between equities and defensive assets."""
    try:
        vix = _last_close("^VIX")
        sp_change = None
        try:
            hist = yf.Ticker("^GSPC").history(period="1mo")
            if hist is not None and not hist.empty and len(hist) >= 2:
                sp_change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
        except Exception:
            pass
        parts = []
        parts.append(f"VIX: {round(vix, 2) if vix is not None else 'N/A'}")
        parts.append(
            f"S&P 500 1-month change: {round(sp_change, 2)}%" if sp_change is not None
            else "S&P 500 1-month change: N/A"
        )
        return "Risk Sentiment: " + ", ".join(parts)
    except Exception as e:
        return f"Risk Sentiment: Data unavailable ({str(e)})"


@tool
@cached_tool(TTL_USD_INDEX)
def get_usd_index() -> str:
    """Fetches the current USD Index (DXY) value - silver is dollar-denominated globally,
    same mechanism as gold."""
    try:
        price = _last_close("DX-Y.NYB")
        if price is None:
            return "USD Index (DXY): Data unavailable (Yahoo did not return a price)"
        return f"USD Index (DXY): {round(price, 2)}"
    except Exception as e:
        return f"USD Index: Data unavailable ({str(e)})"


def get_silver_price():
    """Fetches the current silver futures price (not an @tool, used only for the UI ticker).
    Uses history() instead of the heavier .info endpoint, which is unreliable on
    cloud-hosted IPs (Yahoo Finance frequently blocks/rate-limits .info there)."""
    try:
        hist = yf.Ticker("SI=F").history(period="5d", interval="1d")
        closes = hist["Close"].dropna()
        if len(closes) < 2:
            return None, None, None
        price = round(float(closes.iloc[-1]), 2)
        prev = round(float(closes.iloc[-2]), 2)
        change = round(price - prev, 2)
        pct = round((change / prev) * 100, 2) if prev else 0
        return price, change, pct
    except Exception:
        return None, None, None
