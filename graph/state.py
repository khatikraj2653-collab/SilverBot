from typing import TypedDict, Annotated

# Each factor is set by exactly one subgraph in a parallel fan-out. When a
# subgraph finishes, LangGraph emits every field it holds — including empty
# strings for the factors the OTHER subgraph owned. Plain "last write wins"
# then overwrites real data with those empties, which leaves generate_prediction
# with only one subgraph's factors populated (seen live 2026-11-09: only the
# monetary group reached scoring; all three industrial factors were empty and
# were scored 0). Keeping the first non-empty write prevents that without
# needing output-key filters on the subgraphs.
def _keep_non_empty_str(old: str, new: str) -> str:
    return new if new else (old or "")


def _keep_non_empty_dict(old: dict, new: dict) -> dict:
    return new if new else (old or {})


class SilverState(TypedDict):
    # Monetary factors
    rate_environment: Annotated[str, _keep_non_empty_str]
    gold_silver_ratio: Annotated[str, _keep_non_empty_str]
    risk_sentiment: Annotated[str, _keep_non_empty_str]
    usd_index: Annotated[str, _keep_non_empty_str]
    geopolitical_risk: Annotated[str, _keep_non_empty_str]
    inflation_expectations: Annotated[str, _keep_non_empty_str]

    # Industrial factors
    mining_supply_growth: Annotated[str, _keep_non_empty_str]
    solar_panel_demand: Annotated[str, _keep_non_empty_str]
    industrial_production: Annotated[str, _keep_non_empty_str]

    # Final output
    prediction: Annotated[str, _keep_non_empty_str]
    scores: Annotated[dict, _keep_non_empty_dict]
