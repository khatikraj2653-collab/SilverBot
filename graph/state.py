from typing import TypedDict, Annotated

class SilverState(TypedDict):
    # Monetary factors
    rate_environment: Annotated[str, lambda old, new: new]
    gold_silver_ratio: Annotated[str, lambda old, new: new]
    risk_sentiment: Annotated[str, lambda old, new: new]
    usd_index: Annotated[str, lambda old, new: new]
    geopolitical_risk: Annotated[str, lambda old, new: new]
    inflation_expectations: Annotated[str, lambda old, new: new]

    # Industrial factors
    mining_supply_growth: Annotated[str, lambda old, new: new]
    solar_panel_demand: Annotated[str, lambda old, new: new]
    industrial_production: Annotated[str, lambda old, new: new]

    # Final output
    prediction: Annotated[str, lambda old, new: new]
    scores: Annotated[dict, lambda old, new: new]
