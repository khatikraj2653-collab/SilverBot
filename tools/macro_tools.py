import os
from langchain_core.tools import tool
from fredapi import Fred
from dotenv import load_dotenv
from tools.cache_utils import cached_tool, TTL_RATE_ENV, TTL_WEEKLY

load_dotenv()
fred = Fred(api_key=os.getenv("FRED_API_KEY"))


@tool
@cached_tool(TTL_RATE_ENV)
def get_rate_environment() -> str:
    """Fetches Fed Funds Rate and 10Y TIPS Real Yield from FRED, combined into one
    'Rate Environment' signal since both drive silver via the same opportunity-cost mechanism."""
    try:
        fed_rate = fred.get_series('FEDFUNDS').iloc[-1]
        real_yield = fred.get_series('DFII10').iloc[-1]
        return f"Fed Rate: {round(float(fed_rate), 2)}%, Real Yields (10Y TIPS): {round(float(real_yield), 2)}%"
    except Exception as e:
        return f"Rate Environment: Data unavailable ({str(e)})"


@tool
@cached_tool(TTL_RATE_ENV)
def get_inflation_expectations() -> str:
    """Fetches the 5-Year Breakeven Inflation Rate from FRED, a market-based measure of expected inflation."""
    try:
        value = fred.get_series('T5YIE').iloc[-1]
        return f"5-Year Breakeven Inflation Expectations: {round(float(value), 2)}%"
    except Exception as e:
        return f"Inflation Expectations: Data unavailable ({str(e)})"


@tool
@cached_tool(TTL_WEEKLY)
def get_industrial_production() -> str:
    """Fetches the Industrial Production Index from FRED - measures actual factory/mining/utility
    output, a direct proxy for industrial silver demand (electronics, solar, EVs)."""
    try:
        series = fred.get_series('INDPRO')
        latest = series.iloc[-1]
        year_ago = series.iloc[-13] if len(series) > 13 else series.iloc[0]
        pct_change = ((latest - year_ago) / year_ago) * 100
        return f"Industrial Production Index: {round(float(latest), 2)} (YoY change: {round(float(pct_change), 2)}%)"
    except Exception as e:
        return f"Industrial Production Index: Data unavailable ({str(e)})"