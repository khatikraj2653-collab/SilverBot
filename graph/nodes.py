import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from graph.state import SilverState
from rag.retriever import retrieve_factor_context

llm = ChatOpenAI(
    model="gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0
)

llm_retry = ChatOpenAI(
    model="gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.4
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

Score every factor that has real data, using the full -10 to +10 range. Be decisive — a Gold-Silver Ratio above 80 is silver-bullish (undervalued vs gold), a Rate Environment with rising rates is silver-bearish (opportunity cost), a strong USD Index is silver-bearish, elevated Industrial Production is silver-bullish (industrial demand). Do NOT default to 0 Neutral just because you are uncertain — pick a direction and a magnitude for every factor with real data.

NARROW EXCEPTION — score exactly 0 (Neutral) ONLY IF the factor's Data field is literally missing or errored, meaning it contains "Data unavailable", "Too Many Requests", "Rate limited", "Not enough", "no usable content", or is "N/A" standing alone with no accompanying numeric data. For every OTHER factor with real data (even if the signal is mild), give it a real non-zero score. The Context section is general background only — ignore it when scoring; score based on the current Data value.

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

Identify the bullish (score > 0) and bearish (score < 0) factors by weight x score.

IMPORTANT RULES:
- List up to 3 bullish factors, but ONLY ones with score > 0. If fewer than 3 have a positive score, list only those that do. If none have a positive score, write "none" after BULLISH_FACTORS:.
- List up to 3 bearish factors, but ONLY ones with score < 0. If fewer than 3 have a negative score, list only those that do. If none have a negative score, write "none" after BEARISH_FACTORS:.
- NEVER list a factor with score 0 (Neutral) in either list.

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


def _extract_number(s):
    """Extract the actual numeric value from a factor string. Takes the first
    number AFTER the first colon, so labels like '5-Year Breakeven' don't
    contaminate the extraction with a number from the label itself."""
    import re
    if not isinstance(s, str):
        return None
    tail = s.split(":", 1)[1] if ":" in s else s
    m = re.search(r'-?\d+\.?\d*', tail)
    if not m:
        return None
    try:
        return float(m.group(0))
    except (ValueError, TypeError):
        return None


def _suggest_silver_score(factor_key, raw):
    v = _extract_number(raw)
    if v is None:
        return None
    if factor_key == "rate_environment":
        # Rate Environment extracts Fed Rate first. Higher rates = silver bearish.
        if v < 2.5: return 5
        if v < 3.5: return 3
        if v < 4.5: return -2
        if v < 5: return -5
        return -7
    if factor_key == "gold_silver_ratio":
        # High ratio = silver undervalued relative to gold = bullish
        if v < 50: return -4
        if v < 65: return -1
        if v < 80: return 2
        if v < 95: return 5
        return 7
    if factor_key == "usd_index":
        # Stronger USD = silver bearish
        if v < 95: return 4
        if v < 100: return 2
        if v < 102: return -2
        if v < 105: return -4
        return -6
    if factor_key == "inflation_expectations":
        if v < 2: return -2
        if v < 2.3: return -1
        if v < 2.6: return 2
        if v < 3: return 4
        return 5
    return None


HINTABLE_FACTORS = {"rate_environment", "gold_silver_ratio", "usd_index", "inflation_expectations"}


def generate_prediction(state: SilverState) -> dict:
    from tools.cache_utils import _looks_like_error
    rag_context = {
        key: retrieve_factor_context(query)
        for key, query in FACTOR_RAG_QUERIES.items()
    }

    prompt_inputs = {key: state.get(key, "N/A") for key in FACTOR_WEIGHTS}
    for key in FACTOR_WEIGHTS:
        prompt_inputs[f"{key}_context"] = rag_context.get(key, "N/A")

    rendered_messages = scoring_prompt.format_messages(**prompt_inputs)
    scoring_response = llm.invoke(rendered_messages)

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

    def _parse(raw):
        import re
        out = {}
        for line in raw.split("\n"):
            cleaned = re.sub(r'^[\s\-\*\d\.\`]*\**\s*', '', line).strip().rstrip('*').strip()
            for score_key, factor_key in score_map.items():
                if cleaned.startswith(score_key + ":"):
                    tail = cleaned.split(":", 1)[-1]
                    m = re.search(r'-?\d+', tail)
                    if m:
                        try:
                            out[factor_key] = max(-10, min(10, int(m.group(0))))
                        except (ValueError, TypeError):
                            out[factor_key] = 0
                    else:
                        out[factor_key] = 0
                    break
        return out

    scores = _parse(scoring_response.content)
    for key in FACTOR_WEIGHTS:
        if key not in scores:
            scores[key] = 0

    from tools.cache_utils import _looks_like_error
    for key in FACTOR_WEIGHTS:
        if _looks_like_error(str(state.get(key, ""))):
            scores[key] = 0

    # LLM self-correction loop: if the LLM picked 0 for factors with real
    # data, hand it back its own response with the offender list and ask
    # to re-score. Pure LLM-only, max 2 retries.
    for attempt in range(2):
        zero_offenders = [
            (k, str(state.get(k, ""))[:150])
            for k in score_map.values()
            if scores.get(k, 0) == 0 and not _looks_like_error(str(state.get(k, "")))
        ]
        if not zero_offenders:
            break
        offender_list = "\n".join(f"- {k}: '{v}'" for k, v in zero_offenders)
        complaint = (
            f"YOUR PREVIOUS RESPONSE IS REJECTED. You scored {len(zero_offenders)} factors as 0 "
            f"despite them having REAL DATA. 0 is ONLY for missing data — these all have real "
            f"data and MUST be scored non-zero.\n\n"
            f"The following scores MUST be changed to a non-zero integer -10 to +10:\n"
            f"{offender_list}\n\n"
            f"Even mild signals deserve ±1 or ±2. 0 means 'no signal exists' — these all have signal.\n\n"
            f"Re-output ALL 9 scores in the exact same format. Every factor above MUST be non-zero."
        )
        retry_response = llm_retry.invoke(
            rendered_messages
            + [AIMessage(content=scoring_response.content), HumanMessage(content=complaint)]
        )
        scoring_response = retry_response
        scores = _parse(retry_response.content)
        for key in FACTOR_WEIGHTS:
            if key not in scores:
                scores[key] = 0
        for key in FACTOR_WEIGHTS:
            if _looks_like_error(str(state.get(key, ""))):
                scores[key] = 0

    # OPTION B: Python owns numeric-factor scores via band tables. Overrides
    # the LLM for these factors; text-heavy factors (mining supply, solar
    # demand, geopolitical) remain fully LLM-scored.
    for factor_key in HINTABLE_FACTORS:
        raw = str(state.get(factor_key, ""))
        if _looks_like_error(raw):
            continue
        python_score = _suggest_silver_score(factor_key, raw)
        if python_score is not None:
            scores[factor_key] = python_score

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