import os
import sqlite3
import streamlit as st
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from graph.state import SilverState
from graph.nodes import generate_prediction
from graph.subgraphs import build_industrial_subgraph, build_monetary_subgraph

# Wipe any stale error rows cached under the old behaviour on first import.
try:
    from tools.cache_utils import purge_error_cache
    _purged = purge_error_cache()
    if _purged:
        print(f"[cache] purged {_purged} stale error rows", flush=True)
except Exception as _e:
    print(f"[cache] purge skipped: {_e}", flush=True)


# NOTE: do NOT @st.cache_resource — the compiled graph captures function
# references at build time, which pins old code across deploys.
def build_graph():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'silverbot_checkpoints.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    graph = StateGraph(SilverState)

    graph.add_node("fetch_industrial", build_industrial_subgraph())
    graph.add_node("fetch_monetary", build_monetary_subgraph())
    graph.add_node("generate_prediction", generate_prediction)

    graph.add_edge(START, "fetch_industrial")
    graph.add_edge(START, "fetch_monetary")
    graph.add_edge("fetch_industrial", "generate_prediction")
    graph.add_edge("fetch_monetary", "generate_prediction")
    graph.add_edge("generate_prediction", END)

    return graph.compile(checkpointer=checkpointer)


app = build_graph()