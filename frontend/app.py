import streamlit as st
import os
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from log_client import log_event
from chat_bubble import render_chat_bubble

st.set_page_config(
    page_title="SilverBot - AI Silver Dual-Regime Analyser",
    page_icon="::",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Full-screen loader shown IMMEDIATELY so users don't see a blank page while
# the heavy imports and landing HTML render on first visit.
# Cleared at the end of the script.
_loading_placeholder = st.empty()
_loading_placeholder.markdown(
    """
    <div style="position:fixed;inset:0;display:flex;align-items:center;justify-content:center;
                background:#171B21;z-index:999999;flex-direction:column;gap:14px;">
      <div style="width:44px;height:44px;border:3px solid rgba(192,192,192,.2);
                  border-top-color:#C0C0C0;border-radius:50%;
                  animation:sv-ld 0.9s linear infinite;"></div>
      <div style="color:#C7D1DF;font-family:Inter,sans-serif;font-size:14px;">
        Loading SilverBot…
      </div>
      <style>@keyframes sv-ld{to{transform:rotate(360deg)}}</style>
    </div>
    """,
    unsafe_allow_html=True,
)

# SEO tags injected into the real top-level document (st.markdown runs in
# Streamlit's own DOM, unlike st.components.v1.html which sandboxes into an
# iframe Google's crawler won't associate with this page's <head>).
st.markdown("""
<script>
(function() {
  document.title = "SilverBot — AI Silver Dual-Regime Analyser";
  function setMeta(attr, key, content) {
    let el = document.querySelector(`meta[${attr}="${key}"]`);
    if (!el) { el = document.createElement('meta'); el.setAttribute(attr, key); document.head.appendChild(el); }
    el.setAttribute('content', content);
  }
  const desc = "9-factor AI agent testing whether industrial demand or monetary/safe-haven demand dominates silver right now, built by Raj Tejpal Khatik.";
  setMeta('name', 'description', desc);
  setMeta('property', 'og:title', "SilverBot — AI Silver Dual-Regime Analyser");
  setMeta('property', 'og:description', desc);
  setMeta('property', 'og:type', 'website');
  setMeta('property', 'og:url', 'https://silverbot-raj.streamlit.app/');
  setMeta('property', 'og:image', 'https://raw.githubusercontent.com/khatikraj2653-collab/SilverBot/main/silverbot-demo.gif');
  setMeta('property', 'og:image:width', '1200');
  setMeta('property', 'og:image:height', '630');
  setMeta('property', 'og:image:alt', 'SilverBot — AI Silver Dual-Regime Analyser');
  setMeta('name', 'twitter:card', 'summary_large_image');
  setMeta('name', 'twitter:title', "SilverBot — AI Silver Dual-Regime Analyser");
  setMeta('name', 'twitter:description', desc);
  setMeta('name', 'twitter:image', 'https://raw.githubusercontent.com/khatikraj2653-collab/SilverBot/main/silverbot-demo.gif');

  let canonical = document.querySelector('link[rel="canonical"]');
  if (!canonical) { canonical = document.createElement('link'); canonical.setAttribute('rel', 'canonical'); document.head.appendChild(canonical); }
  canonical.setAttribute('href', 'https://silverbot-raj.streamlit.app/');

  if (!document.getElementById('silverbot-jsonld')) {
    const s = document.createElement('script');
    s.type = 'application/ld+json';
    s.id = 'silverbot-jsonld';
    s.textContent = JSON.stringify({
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      "name": "SilverBot",
      "applicationCategory": "FinanceApplication",
      "operatingSystem": "Web",
      "url": "https://silverbot-raj.streamlit.app/",
      "description": desc,
      "author": {
        "@type": "Person",
        "name": "Raj Tejpal Khatik",
        "sameAs": [
          "https://www.linkedin.com/in/raj-khatik-6ab086395",
          "https://github.com/khatikraj2653-collab",
          "https://portfolio-raj.pages.dev/"
        ]
      }
    });
    document.head.appendChild(s);
  }
})();
</script>
""", unsafe_allow_html=True)

# Google Analytics (GA4)
st.markdown("""
<script async src="https://www.googletagmanager.com/gtag/js?id=G-08KC1B3BFV"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-08KC1B3BFV');
</script>
""", unsafe_allow_html=True)

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
    background: #0C1014 !important;
}

[data-testid="stPageLink"] {
    position: fixed !important;
    top: 14px !important;
    right: 48px !important;
    z-index: 99999 !important;
    width: auto !important;
}
[data-testid="stPageLink"] a {
    background: radial-gradient(120% 90% at 30% 0%, rgba(255,255,255,.85), rgba(255,255,255,0) 55%), linear-gradient(180deg, #BFE0FF, #7FB6EE) !important;
    color: #14171A !important;
    border: 1px solid rgba(255,255,255,.55) !important;
    border-radius: 99px !important;
    padding: 9px 22px !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    font-family: 'Inter', sans-serif !important;
    box-shadow: inset 0 1px 0 #fff, 0 10px 28px -6px rgba(110,170,235,.6) !important;
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

if "visit_logged" not in st.session_state:
    log_event("visit", detail="landing page")
    st.session_state.visit_logged = True

st.page_link("pages/analysis.py", label="Get Started ->")

landing_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'landing.html')
with open(landing_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

iframe_fixes = """
<style>
#welcomeModal { display: none !important; }
body { background: #0C1014 !important; }
#hero { min-height: 650px !important; padding-top: 40px !important; }
.nav-cta { display: none !important; }
.nav { justify-content: center !important; gap: 60px !important; }
.nav-logo { position: absolute !important; left: 48px !important; }
</style>
"""
html_content = html_content.replace('<head>', '<head>' + iframe_fixes)

st.components.v1.html(html_content, height=5900, scrolling=True)

render_chat_bubble()

# Clear the full-screen loader now that the landing page has rendered.
_loading_placeholder.empty()