from langgraph.graph import StateGraph, START, END
from graph.state import SilverState
from tools.macro_tools import get_rate_environment, get_inflation_expectations, get_industrial_production
from tools.market_tools import get_gold_silver_ratio, get_risk_sentiment, get_usd_index
from tools.external_tools import get_mining_supply_growth, get_solar_panel_demand, get_geopolitical_risk


def fetch_mining_supply_node(state: SilverState) -> dict:
    return {"mining_supply_growth": get_mining_supply_growth.invoke({})}

def fetch_solar_demand_node(state: SilverState) -> dict:
    return {"solar_panel_demand": get_solar_panel_demand.invoke({})}

def fetch_industrial_production_node(state: SilverState) -> dict:
    return {"industrial_production": get_industrial_production.invoke({})}


def build_industrial_subgraph():
    subgraph = StateGraph(SilverState)
    subgraph.add_node("fetch_mining_supply", fetch_mining_supply_node)
    subgraph.add_node("fetch_solar_demand", fetch_solar_demand_node)
    subgraph.add_node("fetch_industrial_production", fetch_industrial_production_node)

    subgraph.add_edge(START, "fetch_mining_supply")
    subgraph.add_edge(START, "fetch_solar_demand")
    subgraph.add_edge(START, "fetch_industrial_production")
    subgraph.add_edge("fetch_mining_supply", END)
    subgraph.add_edge("fetch_solar_demand", END)
    subgraph.add_edge("fetch_industrial_production", END)

    return subgraph.compile()


def fetch_rate_environment_node(state: SilverState) -> dict:
    return {"rate_environment": get_rate_environment.invoke({})}

def fetch_gold_silver_ratio_node(state: SilverState) -> dict:
    return {"gold_silver_ratio": get_gold_silver_ratio.invoke({})}

def fetch_risk_sentiment_node(state: SilverState) -> dict:
    return {"risk_sentiment": get_risk_sentiment.invoke({})}

def fetch_usd_index_node(state: SilverState) -> dict:
    return {"usd_index": get_usd_index.invoke({})}

def fetch_geopolitical_risk_node(state: SilverState) -> dict:
    return {"geopolitical_risk": get_geopolitical_risk.invoke({})}

def fetch_inflation_expectations_node(state: SilverState) -> dict:
    return {"inflation_expectations": get_inflation_expectations.invoke({})}


def build_monetary_subgraph():
    subgraph = StateGraph(SilverState)
    subgraph.add_node("fetch_rate_environment", fetch_rate_environment_node)
    subgraph.add_node("fetch_gold_silver_ratio", fetch_gold_silver_ratio_node)
    subgraph.add_node("fetch_risk_sentiment", fetch_risk_sentiment_node)
    subgraph.add_node("fetch_usd_index", fetch_usd_index_node)
    subgraph.add_node("fetch_geopolitical_risk", fetch_geopolitical_risk_node)
    subgraph.add_node("fetch_inflation_expectations", fetch_inflation_expectations_node)

    subgraph.add_edge(START, "fetch_rate_environment")
    subgraph.add_edge(START, "fetch_gold_silver_ratio")
    subgraph.add_edge(START, "fetch_risk_sentiment")
    subgraph.add_edge(START, "fetch_usd_index")
    subgraph.add_edge(START, "fetch_geopolitical_risk")
    subgraph.add_edge(START, "fetch_inflation_expectations")
    subgraph.add_edge("fetch_rate_environment", END)
    subgraph.add_edge("fetch_gold_silver_ratio", END)
    subgraph.add_edge("fetch_risk_sentiment", END)
    subgraph.add_edge("fetch_usd_index", END)
    subgraph.add_edge("fetch_geopolitical_risk", END)
    subgraph.add_edge("fetch_inflation_expectations", END)

    return subgraph.compile()