"""
Interactive causal map: an SVG/JS widget that shows the 9 factors feeding the
Industrial and Monetary regime scores and lets the user run "what if?" scenarios
in the browser.

The weights and formulas mirror graph/nodes.py (FACTOR_WEIGHTS,
calculate_category_strength, calculate_strength); nothing here changes the
stored analysis.
"""
import json
import os

import streamlit.components.v1 as components

FACTOR_KEYS = [
    "mining_supply_growth", "solar_panel_demand", "industrial_production",
    "rate_environment", "gold_silver_ratio", "risk_sentiment",
    "usd_index", "geopolitical_risk", "inflation_expectations",
]

_TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "causal_map.html")


def render_causal_map(scores, notes=None, height=780):
    """Render the interactive map for one analysis result."""
    with open(_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    clean_scores = {}
    for k in FACTOR_KEYS:
        try:
            clean_scores[k] = int((scores or {}).get(k, 0))
        except (TypeError, ValueError):
            clean_scores[k] = 0
    clean_notes = {k: str(v)[:900] for k, v in (notes or {}).items() if v}

    payload = json.dumps({"scores": clean_scores, "notes": clean_notes})
    payload = payload.replace("</", "<\\/")  # keep the JSON from closing the <script> tag
    components.html(html.replace("__CM_DATA__", payload), height=height, scrolling=False)
