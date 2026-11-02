import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from graph.state import SilverState
from rag.retriever import retrieve_factor_context

llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0
)

FACTOR_WEIGHTS = {
    "rate_environment": 14,
    "gold_silver_ratio": 13,
    "risk_sentiment": 12,
    "mining_supply_growth": 12,
    "solar_panel_demand": 11,
    "usd_index": 10,
    "industrial_production": 10,
    "geopolitical_risk": 9,
    "inflation_expectations": 9,
}

INDUSTRIAL_FACTORS = ["mining_supply_growth", "solar_panel_demand", "industrial_production"]
MONETARY_FACTORS = ["rate_environment", "gold_silver_ratio", "risk_sentiment", "usd_index", "geopolitical_risk", "inflation_expectations"]

FACTOR_RAG_QUERIES = {
    "rate_environment": "Fed rate real yields TIPS silver relationship",
    "gold_silver_ratio": "gold silver ratio mean reversion historical relationship",
    "risk_sentiment": "VIX S&P 500 risk sentiment silver relationship",
    "mining_supply_growth": "silver mining supply byproduct copper zinc lead",
    "solar_panel_demand": "solar panel photovoltaic silver industrial demand",
    "usd_index": "USD dollar index silver relationship",
    "industrial_production": "industrial production manufacturing silver demand relationship",
    "geopolitical_risk": "geopolitical conflict war risk silver supply chain",
    "inflation_expectations": "CPI inflation expectations silver hedge relationship",
}


def calculate_category_strength(scores: dict, factor_list: list) -> int:
    """Normalizes a subset of factor scores (e.g. just Industrial or just Monetary)
    against their own weight subtotal, independent of the other category."""
    subtotal_weight = sum(FACTOR_WEIGHTS[k] for k in factor_list)
    weighted_sum = sum(scores[k] * FACTOR_WEIGHTS[k] for k in factor_list)
    max_possible = subtotal_weight * 10
    normalized = (weighted_sum + max_possible) / (2 * max_possible)
    return max(0, min(100, round(normalized * 100)))


def calculate_strength(scores: dict) -> int:
    weighted_sum = sum(scores[k] * FACTOR_WEIGHTS[k] for k in scores)
    normalized = (weighted_sum + 1000) / 2000
    strength = max(0, min(100, round(normalized * 100)))
    return strength


def get_dominant_regime(industrial_pct: int, monetary_pct: int) -> str:
    industrial_bullish = industrial_pct >= 50
    monetary_bullish = monetary_pct >= 50
    if industrial_bullish == monetary_bullish:
        direction = "bullish" if industrial_bullish else "bearish"
        return f"ALIGNED ({direction}) - Industrial and Monetary signals agree"
    else:
        stronger = "Industrial" if abs(industrial_pct - 50) > abs(monetary_pct - 50) else "Monetary"
        return f"DIVERGENT - Industrial demand is {'bullish' if industrial_bullish else 'bearish'} while Monetary/Safe-Haven demand is {'bullish' if monetary_bullish else 'bearish'}. {stronger} signal is currently dominant."


def get_historical_context(limit: int = 5) -> str:
    """Long-term memory: queries past analysis sessions from SQLite (persists across
    threads/sessions) and returns a trend summary the agent can reason over."""
    import sqlite3
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'silverbot_checkpoints.db')
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT status, strength, industrial_pct, monetary_pct, timestamp FROM analysis_history ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return "No prior analysis history available yet."
        summary_lines = [f"{s} ({strength}), Industrial {ind}%, Monetary {mon}% at {ts}" for s, strength, ind, mon, ts in rows]
        return f"Recent analysis history (most recent first): {'; '.join(summary_lines)}."
    except Exception as e:
        return f"Historical context unavailable ({str(e)})"


scoring_prompt = ChatPromptTemplate.from_template("""
You are a silver market analyst. Score each factor from -10 (strongly bearish for silver) to +10 (strongly bullish for silver), given the current data AND the historical context provided for each factor.

FACTOR DATA AND HISTORICAL CONTEXT:

Rate Environment (Fed Rate + Real Yields): {rate_environment}
Context: {rate_environment_context}

Gold-Silver Ratio: {gold_silver_ratio}
Context: {gold_silver_ratio_context}

Risk Sentiment (VIX + S&P 500): {risk_sentiment}
Context: {risk_sentiment_context}

Mining Supply Growth: {mining_supply_growth}
Context: {mining_supply_growth_context}

Solar Panel Demand: {solar_panel_demand}
Context: {solar_panel_demand_context}

USD Index: {usd_index}
Context: {usd_index_context}

Industrial Production Index: {industrial_production}
Context: {industrial_production_context}

Geopolitical Risk: {geopolitical_risk}
Context: {geopolitical_risk_context}

Inflation Expectations: {inflation_expectations}
Context: {inflation_expectations_context}

Return ONLY this exact format, no other text:
RATE_ENVIRONMENT_SCORE: [integer -10 to 10]
GOLD_SILVER_RATIO_SCORE: [integer -10 to 10]
RISK_SENTIMENT_SCORE: [integer -10 to 10]
MINING_SUPPLY_GROWTH_SCORE: [integer -10 to 10]
SOLAR_PANEL_DEMAND_SCORE: [integer -10 to 10]
USD_INDEX_SCORE: [integer -10 to 10]
INDUSTRIAL_PRODUCTION_SCORE: [integer -10 to 10]
GEOPOLITICAL_RISK_SCORE: [integer -10 to 10]
INFLATION_EXPECTATIONS_SCORE: [integer -10 to 10]
""")

reasoning_prompt = ChatPromptTemplate.from_template("""
You are a silver market analyst. Silver has a dual nature: part industrial commodity, part monetary/safe-haven asset. Write a 3-4 sentence reasoning covering:
1. Why the Overall Safe Haven strength scored {strength}%
2. Whether Industrial Strength ({industrial_pct}%) and Monetary Strength ({monetary_pct}%) are aligned or diverging, and what that means
3. Reference the dominant regime: {dominant_regime}

FACTOR SCORES:
{scores_text}

HISTORICAL CONTEXT (past sessions): {historical_context}

Identify the 3 most bullish and 3 most bearish factors (by weight x score).
Format EXACTLY like this:
BULLISH_FACTORS: [factor1] | [factor2] | [factor3]
BEARISH_FACTORS: [factor1] | [factor2] | [factor3]
REASONING: [3-4 sentences]
CONFIDENCE: [High/Medium/Low]
""")

followup_prompt = ChatPromptTemplate.from_template("""
You are SilverBot, an AI assistant specialized in silver market analysis. Silver has a dual nature: ~50% industrial demand (solar, electronics, EVs) and ~50% monetary/safe-haven demand. You understand rate environments, the gold-silver ratio, industrial production, mining supply, geopolitical risk, and the SilverBot system's own architecture and methodology.

STRICT RULE: Only answer questions related to silver, precious metals, industrial commodities, safe-haven assets, macroeconomic factors affecting silver, financial markets broadly, or how SilverBot itself works. If the question is clearly unrelated to these topics, politely decline and redirect the user to ask something relevant to silver or financial markets.

If asked who created you, who built you, or who you were made by, answer: "I was created by Raj Tejpal Khatik."

The context below includes a "long_term_memory_trend" line listing individual past session strengths, industrial %, monetary %, and statuses (most recent first), not just an average. When asked to compare the current result to past sessions, use those individual values directly for the comparison rather than saying you lack the detail.

CURRENT ANALYSIS CONTEXT:
{context}

USER QUESTION: {question}

Answer clearly and concisely in 2-4 sentences, using the context above where relevant. If you don't have enough information in the context to answer precisely, say so honestly rather than guessing.
""")


def generate_prediction(state: SilverState) -> dict:
    rag_context = {
        key: retrieve_factor_context(query)
        for key, query in FACTOR_RAG_QUERIES.items()
    }

    prompt_inputs = {key: state.get(key, "N/A") for key in FACTOR_WEIGHTS}
    for key in FACTOR_WEIGHTS:
        prompt_inputs[f"{key}_context"] = rag_context.get(key, "N/A")

    scoring_response = (scoring_prompt | llm).invoke(prompt_inputs)

    scores = {}
    score_map = {
        "RATE_ENVIRONMENT_SCORE": "rate_environment",
        "GOLD_SILVER_RATIO_SCORE": "gold_silver_ratio",
        "RISK_SENTIMENT_SCORE": "risk_sentiment",
        "MINING_SUPPLY_GROWTH_SCORE": "mining_supply_growth",
        "SOLAR_PANEL_DEMAND_SCORE": "solar_panel_demand",
        "USD_INDEX_SCORE": "usd_index",
        "INDUSTRIAL_PRODUCTION_SCORE": "industrial_production",
        "GEOPOLITICAL_RISK_SCORE": "geopolitical_risk",
        "INFLATION_EXPECTATIONS_SCORE": "inflation_expectations",
    }
    for line in scoring_response.content.split("\n"):
        line = line.strip()
        for score_key, factor_key in score_map.items():
            if line.startswith(score_key + ":"):
                try:
                    scores[factor_key] = int(line.split(":")[-1].strip())
                except:
                    scores[factor_key] = 0
    for key in FACTOR_WEIGHTS:
        if key not in scores:
            scores[key] = 0

    strength = calculate_strength(scores)
    status = "ON" if strength >= 50 else "OFF"
    industrial_pct = calculate_category_strength(scores, INDUSTRIAL_FACTORS)
    monetary_pct = calculate_category_strength(scores, MONETARY_FACTORS)
    industrial_status = "ON" if industrial_pct >= 50 else "OFF"
    monetary_status = "ON" if monetary_pct >= 50 else "OFF"
    dominant_regime = get_dominant_regime(industrial_pct, monetary_pct)

    scores_text = "\n".join([f"{k}: {scores[k]:+d} (weight {FACTOR_WEIGHTS[k]})" for k in FACTOR_WEIGHTS])

    historical_context = get_historical_context()

    reasoning_response = (reasoning_prompt | llm).invoke({
        "strength": strength,
        "industrial_pct": industrial_pct,
        "monetary_pct": monetary_pct,
        "dominant_regime": dominant_regime,
        "scores_text": scores_text,
        "historical_context": historical_context
    })

    final_prediction = (
        f"COMBINED_STATUS: {status}\n"
        f"COMBINED_STRENGTH: {strength}%\n"
        f"INDUSTRIAL_STATUS: {industrial_status}\n"
        f"INDUSTRIAL_STRENGTH: {industrial_pct}%\n"
        f"MONETARY_STATUS: {monetary_status}\n"
        f"MONETARY_STRENGTH: {monetary_pct}%\n"
        f"DOMINANT_REGIME: {dominant_regime}\n"
        f"{reasoning_response.content}"
    )

    return {
        "prediction": final_prediction,
        "scores": scores,
    }


def answer_followup_question(question: str, result: dict) -> str:
    context_parts = []
    context_parts.append(f"long_term_memory_trend: {get_historical_context()}")
    try:
        from tools.market_tools import get_silver_price
        price, change, pct = get_silver_price()
        if price is not None:
            context_parts.append(f"current_silver_price: ${price} ({'+' if change and change >= 0 else ''}{pct}% today)")
    except Exception:
        pass
    for key in ["rate_environment", "gold_silver_ratio", "risk_sentiment", "mining_supply_growth",
                "solar_panel_demand", "usd_index", "industrial_production",
                "geopolitical_risk", "inflation_expectations", "prediction"]:
        if result.get(key):
            context_parts.append(f"{key}: {result[key]}")
    context = "\n".join(context_parts)

    response = (followup_prompt | llm).invoke({
        "context": context,
        "question": question
    })
    return response.content