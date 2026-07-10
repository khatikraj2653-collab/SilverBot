import yfinance as yf
from langchain_core.tools import tool

yf.set_tz_cache_location("D:\\yf_cache")


@tool
def get_gold_silver_ratio() -> str:
    """Fetches the current Gold-Silver Ratio (gold price / silver price) - a historically
    mean-reverting signal unique to silver; extreme ratios often predict silver catch-up rallies."""
    try:
        gold = yf.Ticker("GC=F").info.get('regularMarketPrice')
        silver = yf.Ticker("SI=F").info.get('regularMarketPrice')
        ratio = round(gold / silver, 2) if gold and silver else None
        return f"Gold-Silver Ratio: {ratio} (Gold: ${gold}, Silver: ${silver})"
    except Exception as e:
        return f"Gold-Silver Ratio: Data unavailable ({str(e)})"


@tool
def get_risk_sentiment() -> str:
    """Fetches VIX and S&P 500 1-month growth combined into one 'Risk Sentiment' signal,
    both proxying risk-on/risk-off rotation between equities and defensive assets."""
    try:
        vix = yf.Ticker("^VIX").info.get('regularMarketPrice')
        sp500 = yf.Ticker("^GSPC")
        hist = sp500.history(period="1mo")
        sp_change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
        return f"VIX: {vix}, S&P 500 1-month change: {round(sp_change, 2)}%"
    except Exception as e:
        return f"Risk Sentiment: Data unavailable ({str(e)})"


@tool
def get_usd_index() -> str:
    """Fetches the current USD Index (DXY) value - silver is dollar-denominated globally,
    same mechanism as gold."""
    try:
        dxy = yf.Ticker("DX-Y.NYB")
        price = dxy.info.get('regularMarketPrice')
        return f"USD Index (DXY): {price}"
    except Exception as e:
        return f"USD Index: Data unavailable ({str(e)})"


def get_silver_price():
    """Fetches the current silver futures price (not an @tool, used only for the UI ticker)."""
    try:
        silver = yf.Ticker("SI=F")
        price = silver.info.get('regularMarketPrice')
        prev = silver.info.get('regularMarketPreviousClose')
        change = round(price - prev, 2) if price and prev else 0
        pct = round((change / prev) * 100, 2) if prev else 0
        return price, change, pct
    except Exception as e:
        return None, None, None