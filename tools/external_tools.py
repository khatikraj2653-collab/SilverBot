import os
import re
import json
import asyncio
import concurrent.futures
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


def _clean_text(combined: str) -> str:
    combined = re.sub(r'!\[[^\]]*\]\([^\)]*\)', '', combined)
    combined = re.sub(r'\(https?://[^\)]*\)', '', combined)
    combined = re.sub(r'\[([^\]]+)\]\([^\)]*\)', r'\1', combined)
    combined = re.sub(r'https?://\S+', '', combined)
    combined = re.sub(r'[\[\]]', '', combined)
    combined = re.sub(r'[()]', '', combined)
    combined = re.sub(r'\s+', ' ', combined).strip()
    return combined


def sentence_truncate(text: str, limit: int = 2500) -> str:
    """Truncates at the nearest sentence boundary near `limit`, avoiding mid-sentence cuts."""
    text = str(text)
    if len(text) <= limit:
        return text
    window = text[:limit + 100]
    for punct in ['. ', '! ', '? ']:
        idx = window.rfind(punct, 0, limit + 100)
        if idx != -1 and idx > limit * 0.5:
            return window[:idx + 1].strip()
    return text[:limit].rsplit(' ', 1)[0].strip() + "..."


import concurrent.futures

async def _mcp_tavily_search_async(query: str, max_results: int) -> str:
    client = MultiServerMCPClient({
        "tavily": {
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}",
            "transport": "streamable_http",
        }
    })
    tools = await client.get_tools()
    search_tool = next(t for t in tools if t.name == "tavily_search")
    result = await search_tool.ainvoke({"query": query, "max_results": max_results})

    parsed = json.loads(result[0]["text"])
    contents = [r.get("content", "") for r in parsed.get("results", []) if r.get("content")]
    if not contents:
        raise ValueError("Tavily returned no usable content")

    combined = " ".join(contents)
    return _clean_text(combined)


def _mcp_search_worker(query: str, max_results: int, result_container: dict):
    """Runs inside a completely fresh OS thread with its own brand-new event loop,
    created and destroyed entirely within this thread - never touches Streamlit's loop."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result_container["value"] = loop.run_until_complete(
                _mcp_tavily_search_async(query, max_results)
            )
        finally:
            loop.close()
    except Exception as e:
        result_container["error"] = e


def tavily_search(query: str, max_results: int = 5) -> str:
    """Runs the full MCP client + search call inside a fully isolated worker thread
    with its own dedicated event loop, detached from whatever async context the
    calling thread (e.g. Streamlit) already has."""
    if not TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY not set")

    result_container = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_mcp_search_worker, query, max_results, result_container)
        future.result(timeout=30)

    if "error" in result_container:
        raise result_container["error"]
    return result_container.get("value", "")


@tool
def get_mining_supply_growth() -> str:
    """Searches for recent silver mining supply data - silver is often mined as a byproduct
    of copper/zinc/lead, making supply more inelastic than gold's primary-mined supply."""
    try:
        result = tavily_search("silver mining supply 2026 byproduct production growth", max_results=8)
        return f"Mining Supply Growth: {sentence_truncate(result)}"
    except Exception as e:
        return f"Mining Supply Growth: Data unavailable ({str(e)})"


@tool
def get_solar_panel_demand() -> str:
    """Searches for recent solar panel/photovoltaic demand trends - a genuinely new structural
    silver demand driver, with ~15-20% of global silver demand now going to solar."""
    try:
        result = tavily_search("solar panel photovoltaic silver demand 2026 green energy", max_results=8)
        return f"Solar Panel Demand: {sentence_truncate(result)}"
    except Exception as e:
        return f"Solar Panel Demand: Data unavailable ({str(e)})"


@tool
def get_geopolitical_risk() -> str:
    """Searches for current geopolitical conflict and war risk signals affecting silver via
    both safe-haven demand and mining/supply-chain disruption."""
    try:
        result = tavily_search("geopolitical conflict war risk 2026 silver supply chain", max_results=8)
        return f"Geopolitical Risk: {sentence_truncate(result)}"
    except Exception as e:
        return f"Geopolitical Risk: Data unavailable ({str(e)})"