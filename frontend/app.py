import os
import sys
import time
from zoneinfo import ZoneInfo
from datetime import datetime

UK_TZ = ZoneInfo("Europe/London")

def uk_time_str():
    return datetime.now(UK_TZ).strftime("%Y-%m-%d %H:%M")
import sqlite3
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from dotenv import load_dotenv
from graph.workflow import app
from tools.market_tools import get_silver_price

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "SilverBot")


def get_db_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'silverbot_checkpoints.db')


def init_history_table():
    conn = sqlite3.connect(get_db_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT,
            strength TEXT,
            industrial_pct TEXT,
            monetary_pct TEXT,
            timestamp TEXT,
            result_json TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_history(status, strength, industrial_pct, monetary_pct, timestamp, result):
    conn = sqlite3.connect(get_db_path())
    conn.execute(
        "INSERT INTO analysis_history (status, strength, industrial_pct, monetary_pct, timestamp, result_json) VALUES (?, ?, ?, ?, ?, ?)",
        (status, strength, industrial_pct, monetary_pct, timestamp, json.dumps(result))
    )
    conn.commit()
    conn.close()


def load_history(limit=10):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.execute(
        "SELECT id, status, strength, industrial_pct, monetary_pct, timestamp FROM analysis_history ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "status": r[1], "strength": r[2], "industrial_pct": r[3], "monetary_pct": r[4], "time": r[5]} for r in rows]


def load_history_detail(history_id):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.execute("SELECT result_json FROM analysis_history WHERE id = ?", (history_id,))
    row = cursor.fetchone()
    conn.close()
    return json.loads(row[0]) if row else None


init_history_table()

st.set_page_config(page_title="SilverBot", page_icon="⚪", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;600;700;800&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #14171A !important;
    font-family: 'Inter', sans-serif !important;
}
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
.block-container { padding: 0 !important; padding-bottom: 60px !important; max-width: 100% !important; }

[data-testid="stSidebar"] {
    background: #14171A !important;
    border-right: 1px solid #3A4550 !important;
    min-width: 240px !important; max-width: 240px !important;
}
[data-testid="stSidebar"] * { color: #FFFFFF !important; }

.stButton > button {
    font-family: 'Inter', sans-serif !important; font-weight: 600 !important;
    border-radius: 10px !important; border: none !important;
    background: linear-gradient(135deg, #6B7A88, #C8D4DC) !important;
    color: #14171A !important;
}

.semi-card {
    background: #1E2328; border: 1px solid #3A4550;
    border-radius: 12px; padding: 14px 16px; margin-bottom: 10px;
}
.card-key {
    font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.1em; color: #B8C4CC; margin-bottom: 5px;
}
.card-val { font-size: 0.8rem; color: #DCE4E8; }

.sec-label {
    font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.12em; color: #B8C4CC; margin: 18px 0 10px;
    display: flex; align-items: center; gap: 8px;
}
.sec-label::after { content: ''; flex: 1; height: 1px; background: rgba(184,196,204,0.1); }

.metric-card { border: 1px solid rgba(184,196,204,0.2); border-radius: 12px; padding: 18px 20px; text-align: center; }
.metric-num-on { font-family: 'Space Grotesk', sans-serif; font-size: 1.6rem; font-weight: 700; color: #34D399; }
.metric-num-off { font-family: 'Space Grotesk', sans-serif; font-size: 1.6rem; font-weight: 700; color: #F87171; }
.metric-lbl { font-size: 0.62rem; font-weight: 700; text-transform: uppercase; color: #888; margin-bottom: 8px; }
.bar-track { height: 5px; background: rgba(80,90,100,0.4); border-radius: 3px; margin-top: 10px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 3px; background: linear-gradient(90deg,#6B7A88,#C8D4DC); }

.toggle-switch{ width:56px;height:28px;border-radius:14px; position:relative;margin:0 auto; }
.toggle-on{background:linear-gradient(135deg,#059669,#34D399);box-shadow:0 0 14px rgba(52,211,153,0.5);}
.toggle-off{background:linear-gradient(135deg,#991B1B,#F87171);box-shadow:0 0 14px rgba(248,113,113,0.4);}
.toggle-knob{ width:22px;height:22px;border-radius:50%; background:#FFFFFF;position:absolute;top:3px; box-shadow:0 2px 6px rgba(0,0,0,0.3); }
.toggle-on .toggle-knob{left:31px;}
.toggle-off .toggle-knob{left:3px;}
.toggle-flip{background:linear-gradient(135deg,#6B7A88,#C8D4DC);animation:toggle-flicker 1s ease-in-out infinite;}
@keyframes toggle-flicker{
    0%,100%{background:linear-gradient(135deg,#059669,#34D399);}
    50%{background:linear-gradient(135deg,#991B1B,#F87171);}
}
.toggle-flip .toggle-knob{animation:knob-slide 1s ease-in-out infinite;}
@keyframes knob-slide{
    0%,100%{left:3px;}
    50%{left:31px;}
}

.regime-card {
    background: rgba(107,122,136,0.12); border-left: 3px solid #C8D4DC;
    border-radius: 0 10px 10px 0; padding: 14px 18px;
    font-size: 0.82rem; color: #DCE4E8; line-height: 1.7; margin: 16px 0;
}
.reasoning-card {
    background: rgba(40,45,50,0.55); border-left: 2px solid #C8D4DC;
    border-radius: 0 10px 10px 0; padding: 12px 16px;
    font-size: 0.8rem; color: #B8C4CC; line-height: 1.75; margin-top: 8px;
}
</style>
""", unsafe_allow_html=True)


def smart_truncate(text, limit: int = 2500) -> str:
    text = str(text)
    if len(text) <= limit:
        return text
    window = text[:limit + 80]
    for punct in ['. ', '! ', '? ']:
        idx = window.rfind(punct, 0, limit + 80)
        if idx != -1 and idx > limit * 0.5:
            return window[:idx + 1].strip()
    return text[:limit].rsplit(' ', 1)[0].strip() + "..."


def score_badge(key, scores):
    score = scores.get(key)
    if score is None:
        return ""
    if score > 0:
        color, label = "#34D399", "Bullish"
    elif score < 0:
        color, label = "#F87171", "Bearish"
    else:
        color, label = "#888", "Neutral"
    sign = "+" if score > 0 else ""
    return f"<div style='margin-top:6px;font-size:0.75rem;font-weight:600'><span style='color:#888'>Score: </span><span style='color:{color}'>{sign}{score}</span><span style='color:{color}'>&nbsp;&nbsp;{label}</span></div>"


def parse_prediction(prediction: str) -> dict:
    parsed = {"combined_status": "OFF", "combined_strength": 0, "industrial_status": "OFF",
              "industrial_pct": 0, "monetary_status": "OFF", "monetary_pct": 0,
              "dominant_regime": "", "reasoning": "", "confidence": "Medium",
              "bullish": [], "bearish": []}
    for line in prediction.split("\n"):
        line = line.strip()
        if line.startswith("COMBINED_STATUS:"):
            parsed["combined_status"] = line.split(":", 1)[-1].strip()
        elif line.startswith("COMBINED_STRENGTH:"):
            try: parsed["combined_strength"] = int(float(line.split(":", 1)[-1].strip().replace("%", "")))
            except: pass
        elif line.startswith("INDUSTRIAL_STATUS:"):
            parsed["industrial_status"] = line.split(":", 1)[-1].strip()
        elif line.startswith("INDUSTRIAL_STRENGTH:"):
            try: parsed["industrial_pct"] = int(float(line.split(":", 1)[-1].strip().replace("%", "")))
            except: pass
        elif line.startswith("MONETARY_STATUS:"):
            parsed["monetary_status"] = line.split(":", 1)[-1].strip()
        elif line.startswith("MONETARY_STRENGTH:"):
            try: parsed["monetary_pct"] = int(float(line.split(":", 1)[-1].strip().replace("%", "")))
            except: pass
        elif line.startswith("DOMINANT_REGIME:"):
            parsed["dominant_regime"] = line.split(":", 1)[-1].strip()
        elif "REASONING:" in line:
            parsed["reasoning"] = line.split("REASONING:", 1)[-1].strip()
        elif "CONFIDENCE:" in line:
            parsed["confidence"] = line.split("CONFIDENCE:", 1)[-1].strip()
        elif "BULLISH_FACTORS:" in line:
            parsed["bullish"] = [x.strip() for x in line.split("BULLISH_FACTORS:", 1)[-1].split("|") if x.strip()]
        elif "BEARISH_FACTORS:" in line:
            parsed["bearish"] = [x.strip() for x in line.split("BEARISH_FACTORS:", 1)[-1].split("|") if x.strip()]
    return parsed


if "result" not in st.session_state:
    st.session_state.result = None
if "history" not in st.session_state:
    st.session_state.history = load_history()
if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"session_{int(time.time())}"
if "followup_history" not in st.session_state:
    st.session_state.followup_history = []

with st.sidebar:
    st.markdown("""
    <div style='display:flex;align-items:center;gap:10px;margin-bottom:4px'>
        <div style='width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,#6B7A88,#C8D4DC);display:flex;align-items:center;justify-content:center;font-size:15px'>⚪</div>
        <span style='font-family:Space Grotesk,sans-serif;font-size:16px;font-weight:700;color:#FFFFFF'>SilverBot</span>
    </div>
    <div style='font-size:0.72rem;color:#AAAAAA;margin-bottom:18px'>9-Factor Dual-Regime Analyser</div>
    """, unsafe_allow_html=True)

    st.markdown("<a href='http://localhost:8504/landing.html' target='_self' style='display:block;width:100%;text-align:center;background:linear-gradient(135deg,#6B7A88,#C8D4DC);color:#14171A;padding:10px;border-radius:10px;font-weight:600;font-size:0.9rem;text-decoration:none;margin-bottom:8px;'>Home</a>", unsafe_allow_html=True)

    if st.button("+ New Analysis", use_container_width=True):
        st.session_state.result = None
        st.session_state.followup_history = []
        st.rerun()

    st.markdown("<hr style='border-color:rgba(184,196,204,0.1);margin:14px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.65rem;color:#AAAAAA;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px'>HISTORY</div>", unsafe_allow_html=True)

    if st.session_state.history:
        for item in st.session_state.history[:10]:
            label = f"{item['status']} {item.get('strength','?')} · Ind {item.get('industrial_pct','?')} Mon {item.get('monetary_pct','?')} · {item['time']}"
            if st.button(label, key=f"hist_{item['id']}", use_container_width=True):
                result_r = load_history_detail(item['id'])
                if result_r is not None:
                    st.session_state.result = result_r
                    st.rerun()


if not st.session_state.result:
    st.markdown("""
    <div style='padding:60px 20px 20px;text-align:center'>
        <div style='display:inline-flex;align-items:center;gap:7px;background:rgba(107,122,136,0.15);border:1px solid rgba(184,196,204,0.3);border-radius:20px;padding:5px 14px;font-size:10.5px;font-weight:600;color:#C8D4DC;margin-bottom:20px'>LIVE · 9-Factor Dual-Regime Analysis</div>
        <div style='font-family:Space Grotesk,sans-serif;font-size:1.8rem;font-weight:700;color:#FFFFFF;margin-bottom:8px'>Is Silver Industrial or Monetary Right Now?</div>
        <div style='font-size:0.85rem;color:#B8C4CC;margin-bottom:20px;max-width:600px;margin-left:auto;margin-right:auto;line-height:1.7'>
            SilverBot tests which force is dominating silver right now &mdash; industrial demand or monetary/safe-haven demand &mdash; using 9 real-time causal factors.
        </div>
    </div>
    """, unsafe_allow_html=True)

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'robot_b64.txt'), 'r') as f:
        ROBOT_IMG = f.read()

    hero_robot_html = """
    <style>
    @keyframes rbounce{0%,100%{transform:translateY(0) rotate(0deg);}50%{transform:translateY(-10px) rotate(-3deg);}}
    .hero-robot-img{animation:rbounce 3s ease-in-out infinite;filter:drop-shadow(0 0 24px rgba(184,196,204,0.4)) grayscale(1) brightness(1.3) contrast(0.9);}
    .robot-wrap-outer{position:relative;display:inline-block;}
    .robot-cloud{
        position:absolute;top:-10px;right:-180px;
        background:rgba(30,35,40,0.95);border:1px solid rgba(184,196,204,0.4);
        border-radius:50px;padding:10px 20px;font-size:13px;font-weight:600;
        color:#DCE4E8;white-space:nowrap;opacity:0;
        animation:silver-cloud-cycle 37.5s ease-in-out infinite;
    }
    .robot-cloud::before{
        content:'';position:absolute;width:14px;height:14px;border-radius:50%;
        background:rgba(30,35,40,0.95);border:1px solid rgba(184,196,204,0.4);
        left:10px;bottom:-18px;
    }
    .robot-cloud::after{
        content:'';position:absolute;width:7px;height:7px;border-radius:50%;
        background:rgba(30,35,40,0.95);border:1px solid rgba(184,196,204,0.4);
        left:0px;bottom:-28px;
    }
    .robot-cloud:nth-child(2){animation-delay:0s;}
    .robot-cloud:nth-child(3){animation-delay:2.5s;}
    .robot-cloud:nth-child(4){animation-delay:5s;}
    .robot-cloud:nth-child(5){animation-delay:7.5s;}
    .robot-cloud:nth-child(6){animation-delay:10s;}
    .robot-cloud:nth-child(7){animation-delay:12.5s;}
    .robot-cloud:nth-child(8){animation-delay:15s;}
    .robot-cloud:nth-child(9){animation-delay:17.5s;}
    .robot-cloud:nth-child(10){animation-delay:20s;}
    .robot-cloud:nth-child(11){animation-delay:22.5s;}
    .robot-cloud:nth-child(12){animation-delay:25s;}
    .robot-cloud:nth-child(13){animation-delay:27.5s;}
    .robot-cloud:nth-child(14){animation-delay:30s;}
    .robot-cloud:nth-child(15){animation-delay:32.5s;}
    .robot-cloud:nth-child(16){animation-delay:35s;}
    @keyframes silver-cloud-cycle{
        0%{opacity:0;transform:translateY(6px);}
        1%{opacity:1;transform:translateY(0);}
        7%{opacity:1;transform:translateY(0);}
        8%{opacity:0;transform:translateY(-6px);}
        100%{opacity:0;}
    }
    </style>
    <div style='display:flex;justify-content:center;margin-bottom:16px'>
        <div class='robot-wrap-outer'>
            <img class='hero-robot-img' src='data:image/png;base64,PLACEHOLDER' width='180' style='border-radius:24px;'/>
            <div class='robot-cloud'>Silver: Dual-Regime signal ⚪</div>
            <div class='robot-cloud'>Industrial demand tracked 🏭</div>
            <div class='robot-cloud'>Gold-Silver ratio: live ⚖️</div>
            <div class='robot-cloud'>Solar demand tracked ☀️</div>
            <div class='robot-cloud'>Geopolitical risk: elevated 🌏</div>
            <div class='robot-cloud'>USD Index: tracked live 💵</div>
            <div class='robot-cloud'>Mining supply: monitored ⛏️</div>
            <div class='robot-cloud'>Fed rate: FOMC tracked 🏦</div>
            <div class='robot-cloud'>Inflation expectations: live 📊</div>
            <div class='robot-cloud'>Real yields: tracked live 📉</div>
            <div class='robot-cloud'>VIX: monitored in real-time 😨</div>
            <div class='robot-cloud'>No hallucination scoring 🎯</div>
            <div class='robot-cloud'>RAG-grounded analysis 📚</div>
            <div class='robot-cloud'>Deterministic weighting applied ⚖️</div>
            <div class='robot-cloud'>Divergence detection: live 🛡️</div>
        </div>
    </div>
    """
    hero_robot_html = hero_robot_html.replace("PLACEHOLDER", ROBOT_IMG)
    st.markdown(hero_robot_html, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.markdown("<div style='padding-top:20px;text-align:center'>", unsafe_allow_html=True)
        analyse = st.button("Run Analysis →", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if analyse:
        st.session_state.thread_id = f"session_{int(time.time())}"
        progress_bar = st.progress(0, text="Starting analysis...")
        ph_industrial = st.empty()
        ph_monetary = st.empty()

        def make_cards(data, pairs, label):
            html = f"<div class='sec-label'>{label}</div>"
            for lbl, key in pairs:
                val = smart_truncate(data.get(key, "Loading..."))
                html += f"<div class='semi-card'><div class='card-key'>{lbl}</div><div class='card-val'>{val}</div></div>"
            return html

        result = {}
        nodes_done = 0
        total_nodes = 2

        try:
            for chunk in app.stream(
                {},
                config={"configurable": {"thread_id": st.session_state.thread_id}},
                stream_mode="updates"
            ):
                for node_name, node_data in chunk.items():
                    for k, v in node_data.items():
                        if v:
                            result[k] = v
                    if node_name in ("fetch_industrial", "fetch_monetary"):
                        nodes_done += 1
                        pct = int((nodes_done / total_nodes) * 100)

                        if node_name == "fetch_industrial":
                            progress_bar.progress(pct, text="Industrial factors loaded")
                            ph_industrial.markdown(make_cards(result, [
                                ("Mining Supply Growth", "mining_supply_growth"),
                                ("Solar Panel Demand", "solar_panel_demand"),
                                ("Industrial Production", "industrial_production")
                            ], "Industrial"), unsafe_allow_html=True)

                        elif node_name == "fetch_monetary":
                            progress_bar.progress(pct, text="Monetary factors loaded")
                            ph_monetary.markdown(make_cards(result, [
                                ("Rate Environment", "rate_environment"),
                                ("Gold-Silver Ratio", "gold_silver_ratio"),
                                ("Risk Sentiment", "risk_sentiment"),
                                ("USD Index", "usd_index"),
                                ("Geopolitical Risk", "geopolitical_risk"),
                                ("Inflation Expectations", "inflation_expectations")
                            ], "Monetary / Safe-Haven"), unsafe_allow_html=True)
                    elif node_name == "generate_prediction":
                        progress_bar.progress(100, text="Prediction complete")

            progress_bar.empty()
            st.session_state.result = result

            parsed = parse_prediction(result.get("prediction", ""))
            save_history(parsed["combined_status"], f"{parsed['combined_strength']}%",
                         f"{parsed['industrial_pct']}%", f"{parsed['monetary_pct']}%",
                         uk_time_str(), result)
            st.session_state.history = load_history()
            st.rerun()

        except Exception as e:
            st.error(f"Analysis failed: {str(e)}")

else:
    result = st.session_state.result
    prediction = result.get("prediction", "")
    scores = result.get("scores", {})
    p = parse_prediction(prediction)

    st.markdown("""
    <div style='padding:24px 32px 0'>
        <div style='font-family:Space Grotesk,sans-serif;font-size:1.3rem;font-weight:700;color:#FFFFFF;margin-bottom:4px'>Silver Dual-Regime Analysis</div>
        <div style='font-size:0.75rem;color:#B8C4CC'>9-Factor Agentic RAG · Industrial vs Monetary</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='padding:0 32px'>", unsafe_allow_html=True)

    st.markdown("<div class='sec-label'>Industrial</div>", unsafe_allow_html=True)
    for label, key in [("Mining Supply Growth", "mining_supply_growth"), ("Solar Panel Demand", "solar_panel_demand"), ("Industrial Production", "industrial_production")]:
        st.markdown(f"<div class='semi-card'><div class='card-key'>{label}</div><div class='card-val'>{smart_truncate(result.get(key,'N/A'))}</div>{score_badge(key, scores)}</div>", unsafe_allow_html=True)

    st.markdown("<div class='sec-label'>Monetary / Safe-Haven</div>", unsafe_allow_html=True)
    for label, key in [("Rate Environment", "rate_environment"), ("Gold-Silver Ratio", "gold_silver_ratio"), ("Risk Sentiment", "risk_sentiment"), ("USD Index", "usd_index"), ("Geopolitical Risk", "geopolitical_risk"), ("Inflation Expectations", "inflation_expectations")]:
        st.markdown(f"<div class='semi-card'><div class='card-key'>{label}</div><div class='card-val'>{smart_truncate(result.get(key,'N/A'))}</div>{score_badge(key, scores)}</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:rgba(184,196,204,0.08);margin:24px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='font-family:Space Grotesk,sans-serif;font-size:1rem;font-weight:600;color:#FFFFFF;margin-bottom:14px'>Prediction</div>", unsafe_allow_html=True)

    result_key = str(result.get("prediction", ""))[:50]
    is_new_result = st.session_state.get("last_animated_result") != result_key

    t1, t2, t3 = st.columns(3)
    placeholders = {}
    for col, title in [(t1, "Industrial"), (t2, "Monetary"), (t3, "Combined")]:
        with col:
            ph = st.empty()
            placeholders[title] = ph
            if is_new_result:
                ph.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-lbl'>{title}</div>
                    <div class='toggle-switch toggle-flip'><div class='toggle-knob'></div></div>
                    <div class='metric-lbl' style='margin-top:8px;color:#8A96A0'>Calculating...</div>
                </div>""", unsafe_allow_html=True)

    if is_new_result:
        time.sleep(7)
        st.session_state.last_animated_result = result_key

    for col, title, status, pct in [
        (t1, "Industrial", p["industrial_status"], p["industrial_pct"]),
        (t2, "Monetary", p["monetary_status"], p["monetary_pct"]),
        (t3, "Combined", p["combined_status"], p["combined_strength"]),
    ]:
        tc = "toggle-on" if status == "ON" else "toggle-off"
        sc = "metric-num-on" if status == "ON" else "metric-num-off"
        placeholders[title].markdown(f"""
        <div class='metric-card'>
            <div class='metric-lbl'>{title}</div>
            <div class='toggle-switch {tc}'><div class='toggle-knob'></div></div>
            <div class='{sc}' style='margin-top:8px'>{status}</div>
            <div class='metric-lbl' style='margin-top:10px'>{pct}%</div>
            <div class='bar-track'><div class='bar-fill' style='width:{pct}%'></div></div>
        </div>""", unsafe_allow_html=True)

    st.markdown(f"<div class='regime-card'><strong>Dominant Regime:</strong> {p['dominant_regime']}</div>", unsafe_allow_html=True)

    bullish_html = "".join([f"<div style='font-size:0.8rem;color:#34D399;margin-bottom:4px'>+ {b}</div>" for b in p["bullish"][:3]])
    bearish_html = "".join([f"<div style='font-size:0.8rem;color:#F87171;margin-bottom:4px'>- {b}</div>" for b in p["bearish"][:3]])
    st.markdown(f"""
    <div class='metric-card' style='text-align:left'>
        <div style='display:grid;grid-template-columns:1fr 1fr;gap:16px'>
            <div><div style='font-size:0.62rem;color:#888;font-weight:700;text-transform:uppercase;margin-bottom:8px'>Bullish</div>{bullish_html}</div>
            <div><div style='font-size:0.62rem;color:#888;font-weight:700;text-transform:uppercase;margin-bottom:8px'>Bearish</div>{bearish_html}</div>
        </div>
        <div style='margin-top:12px;font-size:0.7rem;color:#888'>Confidence: <strong style='color:#C8D4DC'>{p['confidence']}</strong></div>
    </div>""", unsafe_allow_html=True)

    if p["reasoning"]:
        st.markdown(f"<div class='reasoning-card'>{p['reasoning']}</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:rgba(184,196,204,0.08);margin:24px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='font-family:Space Grotesk,sans-serif;font-size:1rem;font-weight:600;color:#FFFFFF;margin-bottom:6px'>Ask a follow-up question</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.75rem;color:#8A96A0;margin-bottom:14px'>Ask about factors, silver market behavior, or how SilverBot works</div>", unsafe_allow_html=True)

    for qa in st.session_state.followup_history:
        st.markdown(f"<div style='background:rgba(40,45,50,0.5);border-radius:10px;padding:10px 14px;margin-bottom:8px;font-size:0.8rem;color:#DCE4E8'><strong style='color:#C8D4DC'>You:</strong> {qa['q']}<br><strong style='color:#C8D4DC'>SilverBot:</strong> {qa['a']}</div>", unsafe_allow_html=True)

    q_col1, q_col2 = st.columns([4, 1])
    with q_col1:
        followup_q = st.text_input("Question", placeholder="e.g. Is industrial or monetary demand dominant right now?", label_visibility="collapsed", key="followup_input")
    with q_col2:
        ask_clicked = st.button("Ask →", use_container_width=True)

    if ask_clicked and followup_q.strip():
        from graph.nodes import answer_followup_question
        with st.spinner("Thinking..."):
            answer = answer_followup_question(followup_q.strip(), result)
        st.session_state.followup_history.append({"q": followup_q.strip(), "a": answer})
        st.rerun()

    st.markdown("""
    <div style='background:rgba(80,90,100,0.15);border:1px solid rgba(184,196,204,0.25);border-radius:10px;padding:11px 15px;font-size:0.72rem;color:#B8C4CC;line-height:1.6;margin-top:18px'>
        Warning: This analysis is generated by an AI research tool for informational and academic purposes only.
        It does NOT constitute financial advice. Always consult a qualified financial advisor.
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


current_scores = st.session_state.result.get("scores", {}) if st.session_state.result else {}

@st.cache_data(ttl=900)
def get_ticker_data(scores_snapshot):
    price, change, pct = get_silver_price()
    if price is None:
        return "SILVER (SI=F): N/A"
    arrow = "▲" if change and change >= 0 else "▼"
    color = "#34D399" if change and change >= 0 else "#F87171"
    price_html = f"<span style='margin-right:32px'><strong style='color:#C8D4DC'>SILVER</strong> <span style='color:#DCE4E8'>${price}</span> <span style='color:{color}'>{arrow} {pct}%</span></span>"

    def sig(score):
        if score is None: return "N/A", "#8A96A0"
        if score > 3: return "Bullish", "#34D399"
        if score > 0: return "Mild+", "#34D399"
        if score < -3: return "Bearish", "#F87171"
        if score < 0: return "Mild-", "#F87171"
        return "Neutral", "#8A96A0"

    labels = [("Rate Env", "rate_environment"), ("Gold-Silver Ratio", "gold_silver_ratio"),
              ("Risk Sentiment", "risk_sentiment"), ("Mining Supply", "mining_supply_growth"),
              ("Solar Demand", "solar_panel_demand"), ("USD Index", "usd_index"),
              ("Industrial Prod", "industrial_production"), ("Geo Risk", "geopolitical_risk"),
              ("Inflation Exp", "inflation_expectations")]
    factor_html = ""
    for label, key in labels:
        s, c = sig(scores_snapshot.get(key))
        factor_html += f"<span style='margin-right:32px'><strong style='color:#B8C4CC'>{label}</strong> <span style='color:{c};font-weight:600'>{s}</span></span>"
    return price_html + factor_html

ticker_html = get_ticker_data(current_scores)

st.markdown(f"""
<style>
.ticker-wrap {{ position: fixed; bottom: 0; left: 0; right: 0; z-index: 9999; background: #191D22; border-top: 1px solid rgba(184,196,204,0.2); padding: 8px 0; overflow: hidden; }}
.ticker-move {{ display: inline-block; white-space: nowrap; animation: ticker-scroll 40s linear infinite; font-size: 0.78rem; }}
@keyframes ticker-scroll {{ 0% {{ transform: translateX(100vw); }} 100% {{ transform: translateX(-100%); }} }}
</style>
<div class='ticker-wrap'><div class='ticker-move'>{ticker_html}&nbsp;&nbsp;&nbsp;&nbsp;{ticker_html}</div></div>
""", unsafe_allow_html=True)