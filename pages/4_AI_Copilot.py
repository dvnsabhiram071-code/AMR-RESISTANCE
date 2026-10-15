"""
AMR Sentinel - Groq AI Copilot & Explainability Assistant
"""
import streamlit as st
import os
from src.ui_helpers import (
    initialize_session_state,
    render_header,
    require_authentication,
    ACCENT_TEAL,
    BORDER_DARK,
    PANEL_BG,
    TEXT_MUTED
)
from src.alerts import detect_alerts_from_dataframe
from src.copilot import query_amr_copilot, generate_offline_explanation

st.set_page_config(page_title="AMR Sentinel · AI Copilot", page_icon="🤖", layout="wide")
initialize_session_state()
require_authentication()
render_header("AI Surveillance Copilot", "Evidence-grounded, plain-language explanations of AMR anomalies powered by Groq LPU")

raw_df = st.session_state.active_df
alerts = detect_alerts_from_dataframe(raw_df)

if not alerts:
    st.info("No active surveillance alerts to explain in the current dataset.")
    st.stop()

# Select alert to analyze
alert_map = {f"[{a.severity}] {a.id} — {a.organism} vs {a.antibiotic} ({a.department})": a.id for a in alerts}
alert_labels = list(alert_map.keys())

curr_sel_id = st.session_state.get("selected_alert_id", alerts[0].id)
default_idx = 0
for idx, lbl in enumerate(alert_labels):
    if alert_map[lbl] == curr_sel_id:
        default_idx = idx
        break

sel_alert_lbl = st.selectbox("Select Signal for Copilot Interpretation", alert_labels, index=default_idx)
selected_alert_id = alert_map[sel_alert_lbl]
selected_alert = next((a for a in alerts if a.id == selected_alert_id), alerts[0])

# Evidence Inspector Accordion
with st.expander("🔍 View Structured Evidence Fed to Copilot (Source of Truth)", expanded=False):
    st.json(selected_alert.evidence)
    st.caption("ℹ️ The Copilot is mathematically bound to these validated metrics. It cannot invent numbers or alter rates.")

st.markdown("---")

# Pre-set questions or custom prompt
st.subheader("💬 Ask the Copilot")

suggested_queries = [
    "Why was this alert flagged and what evidence supports it?",
    "What are the exact numerators, denominators, and reporting windows?",
    "Could low sample size or missing data bias this signal?",
    "What clinical and laboratory verification steps should infection control take?",
]

selected_query = st.radio("Choose a clinical surveillance question or write your own below:", suggested_queries, index=0)
custom_query = st.text_input("Custom Surveillance Question (Optional):", value="")

final_query = custom_query.strip() if custom_query.strip() else selected_query

col_q1, col_q2 = st.columns([1, 4])
with col_q1:
    ask_btn = st.button("🚀 Analyze with Groq Copilot", type="primary", use_container_width=True)

if ask_btn:
    with st.spinner("Analyzing structured evidence with Groq high-speed LPU inference..."):
        api_key = os.getenv("GROQ_API_KEY")
        response_text = query_amr_copilot(
            evidence=selected_alert.evidence,
            user_query=final_query,
            api_key=api_key
        )
    
    st.markdown("### 📋 Copilot Surveillance Briefing")
    st.markdown(
        f"""
        <div class="amr-card" style="border-left: 4px solid {ACCENT_TEAL}; padding: 20px 24px;">
            {response_text}
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.caption(
        "🔒 **Safety & Compliance Notice:** This Copilot response was generated strictly from the validated "
        "surveillance evidence above. It is an epidemiological decision-support prototype and does not provide clinical "
        "diagnoses or individual antibiotic prescriptions."
    )
