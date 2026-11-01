# SilverBot

AI dual-regime silver analyser — an agentic research tool that evaluates silver as both an industrial and a safe-haven asset.

**Live app:** https://silverbot-raj.streamlit.app/

## Key results
Separate Industrial and Monetary strength scores. Industrial signals beat Monetary in 3 of 4 regimes (61.7% vs 40.0%, p=0.041 in the largest sample), but the pattern reverses in the 2020 liquidity crisis (Monetary 95.0% vs Industrial 65.0%). Research paper: SSRN 7203201 (under review).

## Demo
![SilverBot demo](silverbot-demo.gif)

## Stack
- Streamlit (frontend)
- LangGraph + LangChain (agent orchestration, MCP adapters)
- RAG pipeline (FAISS + sentence-transformers embeddings)
- FRED and Yahoo Finance data (fredapi, yfinance)

## Architecture

```mermaid
flowchart TD
    START([START]) --> fetch_industrial
    START --> fetch_monetary

    subgraph fetch_industrial["fetch_industrial (subgraph)"]
        direction TB
        i_start([START]) --> fetch_mining_supply
        i_start --> fetch_solar_demand
        i_start --> fetch_industrial_production
        fetch_mining_supply --> i_end([END])
        fetch_solar_demand --> i_end
        fetch_industrial_production --> i_end
    end

    subgraph fetch_monetary["fetch_monetary (subgraph)"]
        direction TB
        m_start([START]) --> fetch_rate_environment
        m_start --> fetch_gold_silver_ratio
        m_start --> fetch_risk_sentiment
        m_start --> fetch_usd_index
        m_start --> fetch_geopolitical_risk
        m_start --> fetch_inflation_expectations
        fetch_rate_environment --> m_end([END])
        fetch_gold_silver_ratio --> m_end
        fetch_risk_sentiment --> m_end
        fetch_usd_index --> m_end
        fetch_geopolitical_risk --> m_end
        fetch_inflation_expectations --> m_end
    end

    fetch_industrial --> generate_prediction["generate_prediction\n(scores factors, RAG context, LLM reasoning)"]
    fetch_monetary --> generate_prediction
    generate_prediction --> END([END])
```

## Run locally
```bash
pip install -r requirements.txt
streamlit run frontend/app.py
```
