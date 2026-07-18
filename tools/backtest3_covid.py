import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from fredapi import Fred
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from graph.nodes import generate_prediction

fred = Fred(api_key=os.getenv("FRED_API_KEY"))

# Same 20 COVID dates as GoldBot's Backtest 3
TEST_DATES = [
    datetime(2020,1,20), datetime(2020,1,27), datetime(2020,2,6), datetime(2020,2,17),
    datetime(2020,2,21), datetime(2020,3,3), datetime(2020,3,9), datetime(2020,3,18),
    datetime(2020,3,25), datetime(2020,4,1), datetime(2020,4,9), datetime(2020,4,21),
    datetime(2020,4,29), datetime(2020,5,6), datetime(2020,5,12), datetime(2020,5,25),
    datetime(2020,6,1), datetime(2020,6,11), datetime(2020,6,17), datetime(2020,6,25),
]

def fred_value_as_of(series_id, as_of_date):
    try:
        series = fred.get_series(series_id)
        series = series[series.index <= pd.Timestamp(as_of_date)]
        if series.empty:
            return None
        return float(series.iloc[-1])
    except Exception:
        return None

def fred_yoy_as_of(series_id, as_of_date):
    try:
        series = fred.get_series(series_id)
        series = series[series.index <= pd.Timestamp(as_of_date)]
        if len(series) < 13:
            return None, None
        latest = float(series.iloc[-1])
        year_ago = float(series.iloc[-13])
        pct_change = ((latest - year_ago) / year_ago) * 100
        return latest, pct_change
    except Exception:
        return None, None

def yf_close_as_of(ticker_symbol, as_of_date, lookback_days=10):
    try:
        t = yf.Ticker(ticker_symbol)
        start = as_of_date - timedelta(days=lookback_days)
        end = as_of_date + timedelta(days=1)
        hist = t.history(start=start, end=end)
        if hist.empty:
            return None
        return float(hist['Close'].iloc[-1])
    except Exception:
        return None

def sp500_growth_as_of(as_of_date):
    try:
        t = yf.Ticker("^GSPC")
        start = as_of_date - timedelta(days=35)
        end = as_of_date + timedelta(days=1)
        hist = t.history(start=start, end=end)
        if len(hist) < 2:
            return None
        change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
        return round(change, 2)
    except Exception:
        return None

def price_vs_ma50(ticker_symbol, as_of_date):
    try:
        t = yf.Ticker(ticker_symbol)
        start = as_of_date - timedelta(days=80)
        end = as_of_date + timedelta(days=1)
        hist = t.history(start=start, end=end)
        if len(hist) < 50:
            return None, None
        ma50 = hist['Close'].rolling(50).mean().iloc[-1]
        price = hist['Close'].iloc[-1]
        return round(float(price), 2), round(float(ma50), 2)
    except Exception:
        return None, None

def classify_regime_vs_proxy(target_price, target_ma50, proxy_price, proxy_ma50):
    if None in (target_price, target_ma50, proxy_price, proxy_ma50):
        return None, None, None
    target_above = target_price > target_ma50
    proxy_above = proxy_price > proxy_ma50
    regime = "ALIGNED" if target_above == proxy_above else "DIVERGENT"
    return regime, target_above, proxy_above

def build_historical_state(as_of_date):
    fed_rate = fred_value_as_of('FEDFUNDS', as_of_date)
    real_yield = fred_value_as_of('DFII10', as_of_date)
    inflation_exp = fred_value_as_of('T5YIE', as_of_date)
    indpro_latest, indpro_yoy = fred_yoy_as_of('INDPRO', as_of_date)
    gold_price = yf_close_as_of('GC=F', as_of_date)
    silver_price = yf_close_as_of('SI=F', as_of_date)
    vix = yf_close_as_of('^VIX', as_of_date)
    sp500_growth = sp500_growth_as_of(as_of_date)
    usd_index = yf_close_as_of('DX-Y.NYB', as_of_date)

    if fed_rate is not None and real_yield is not None:
        rate_environment = f"Fed Rate: {round(fed_rate,2)}%, Real Yields (10Y TIPS): {round(real_yield,2)}%"
    else:
        rate_environment = "Rate Environment: Data unavailable"

    if gold_price is not None and silver_price is not None:
        ratio = round(gold_price / silver_price, 2)
        gold_silver_ratio = f"Gold-Silver Ratio: {ratio} (Gold: ${gold_price}, Silver: ${silver_price})"
    else:
        gold_silver_ratio = "Gold-Silver Ratio: Data unavailable"

    if vix is not None and sp500_growth is not None:
        risk_sentiment = f"VIX: {vix}, S&P 500 1-month change: {sp500_growth}%"
    else:
        risk_sentiment = "Risk Sentiment: Data unavailable"

    usd_index_str = f"USD Index (DXY): {round(usd_index,3)}" if usd_index is not None else "USD Index: Data unavailable"

    if indpro_latest is not None:
        industrial_production = f"Industrial Production Index: {round(indpro_latest,2)} (YoY change: {round(indpro_yoy,2)}%)"
    else:
        industrial_production = "Industrial Production Index: Data unavailable"

    inflation_str = f"5-Year Breakeven Inflation Expectations: {round(inflation_exp,2)}%" if inflation_exp is not None else "Inflation Expectations: Data unavailable"

    state = {
        "rate_environment": rate_environment,
        "gold_silver_ratio": gold_silver_ratio,
        "risk_sentiment": risk_sentiment,
        "usd_index": usd_index_str,
        "industrial_production": industrial_production,
        "inflation_expectations": inflation_str,
        "mining_supply_growth": "Mining Supply Growth: Data unavailable (backtest - 2020 predates or bypasses historical text recovery)",
        "solar_panel_demand": "Solar Panel Demand: Data unavailable (backtest - 2020 predates or bypasses historical text recovery)",
        "geopolitical_risk": "Geopolitical Risk: Data unavailable (backtest - 2020 predates or bypasses historical text recovery)",
    }
    tier1_values = [fed_rate, real_yield, inflation_exp, indpro_latest, gold_price, silver_price, vix, sp500_growth, usd_index]
    return state, tier1_values

def run_backtest():
    results = []
    skipped = 0

    for i, as_of_date in enumerate(TEST_DATES):
        print(f"\n[{i+1}/{len(TEST_DATES)}] Testing date: {as_of_date.date()}")

        state, tier1_values = build_historical_state(as_of_date)

        if sum(v is None for v in tier1_values) > 3:
            print("  SKIPPED - too many missing Tier-1 factors")
            skipped += 1
            continue

        try:
            prediction_result = generate_prediction(state)
        except Exception as e:
            print(f"  SKIPPED - generate_prediction failed: {e}")
            skipped += 1
            continue

        pred_text = prediction_result["prediction"]
        combined_status = "ON" if "COMBINED_STATUS: ON" in pred_text else "OFF"
        industrial_status = "ON" if "INDUSTRIAL_STATUS: ON" in pred_text else "OFF"
        monetary_status = "ON" if "MONETARY_STATUS: ON" in pred_text else "OFF"

        silver_price, silver_ma50 = price_vs_ma50("SI=F", as_of_date)
        gold_price_gt, gold_ma50_gt = price_vs_ma50("GC=F", as_of_date)
        copper_price, copper_ma50 = price_vs_ma50("HG=F", as_of_date)

        combined_correct = None
        if silver_price is not None and silver_ma50 is not None:
            silver_above = silver_price > silver_ma50
            combined_correct = (combined_status == "ON") == silver_above

        monetary_regime, silver_above_m, gold_above_m = classify_regime_vs_proxy(silver_price, silver_ma50, gold_price_gt, gold_ma50_gt)
        industrial_regime, silver_above_i, copper_above_i = classify_regime_vs_proxy(silver_price, silver_ma50, copper_price, copper_ma50)

        monetary_correct = None
        if monetary_regime in ("ALIGNED", "DIVERGENT"):
            monetary_correct = (monetary_status == "ON") == gold_above_m

        industrial_correct = None
        if industrial_regime in ("ALIGNED", "DIVERGENT"):
            industrial_correct = (industrial_status == "ON") == copper_above_i

        results.append({
            "date": as_of_date.date().isoformat(),
            "combined_status": combined_status,
            "industrial_status": industrial_status,
            "monetary_status": monetary_status,
            "silver_price": silver_price,
            "silver_ma50": silver_ma50,
            "gold_price": gold_price_gt,
            "gold_ma50": gold_ma50_gt,
            "copper_price": copper_price,
            "copper_ma50": copper_ma50,
            "monetary_regime_gt": monetary_regime,
            "industrial_regime_gt": industrial_regime,
            "combined_correct": combined_correct,
            "monetary_correct": monetary_correct,
            "industrial_correct": industrial_correct,
        })

        print(f"  Combined: {combined_status} | Industrial: {industrial_status} | Monetary: {monetary_status}")
        print(f"  Silver vs MA50: {silver_price} vs {silver_ma50} | Gold-regime GT: {monetary_regime} | Copper-regime GT: {industrial_regime}")

    df = pd.DataFrame(results)
    df.to_csv("backtest3_covid_results.csv", index=False)

    for col in ["combined_correct", "monetary_correct", "industrial_correct"]:
        valid = df[col].dropna()
        acc = valid.mean()*100 if len(valid) > 0 else float('nan')
        print(f"\n{col}: {acc:.1f}% ({int(valid.sum())}/{len(valid)})")

    print("\nSaved to backtest3_covid_results.csv")

if __name__ == "__main__":
    run_backtest()
