import os
import sqlite3
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from graph.state import SilverState
from graph.nodes import generate_prediction
from graph.subgraphs import build_industrial_subgraph, build_monetary_subgraph


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