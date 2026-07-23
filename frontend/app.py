import streamlit as st
import os

st.set_page_config(
    page_title="SilverBot - AI Silver Dual-Regime Analyser",
    page_icon="::",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stDecoration"] { display: none; }
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stSidebarNav"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #14171A !important;
}

[data-testid="stPageLink"] {
    position: fixed !important;
    top: 14px !important;
    right: 48px !important;
    z-index: 99999 !important;
    width: auto !important;
}
[data-testid="stPageLink"] a {
    background: linear-gradient(135deg, #6B7A88, #C8D4DC) !important;
    color: #14171A !important;
    border: none !important;
    border-radius: 9px !important;
    padding: 9px 22px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    box-shadow: 0 0 18px rgba(184,196,204,0.4) !important;
    text-decoration: none !important;
    display: inline-block !important;
}
[data-testid="stPageLink"] a:hover {
    box-shadow: 0 0 30px rgba(200,212,220,0.6) !important;
    transform: translateY(-1px) !important;
}
[data-testid="stPageLink"] svg { display: none !important; }

iframe[title="streamlit_component"] {
    background: transparent !important;
}
</style>
""", unsafe_allow_html=True)

st.page_link("pages/analysis.py", label="Get Started ->")

landing_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'landing.html')
with open(landing_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

iframe_fixes = """
<style>
#welcomeModal { display: none !important; }
body { background: #14171A !important; }
#hero { min-height: 650px !important; padding-top: 40px !important; }
.nav-cta { display: none !important; }
.nav { justify-content: center !important; gap: 60px !important; }
.nav-logo { position: absolute !important; left: 48px !important; }
</style>
"""
html_content = html_content.replace('<head>', '<head>' + iframe_fixes)

st.components.v1.html(html_content, height=2600, scrolling=True)