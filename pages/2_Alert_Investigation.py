"""
AMR Sentinel - Alert Investigation & Clinical Decision Triage
"""
import streamlit as st
import pandas as pd
import plotly.express as go
import plotly.graph_objects as go

from src.ui_helpers import (
    initialize_session_state,
    render_header,
    render_sidebar_filters,
    require_authentication,
    ACCENT_TEAL,
    BORDER_DARK,
    PANEL_BG,
    TEXT_MUTED
)
from src.alerts import detect_alerts_from_dataframe
from src.metrics import calculate_resistance_rate
from src.alarm_manager import GLOBAL_ALARM_MANAGER

st.set_page_config(page_title="AMR Sentinel · Alert Investigation", page_icon="🚨", layout="wide")
initialize_session_state()
require_authentication()
render_header("Alert Investigation & Triage", "Deep-dive clinical audit of surveillance signals with closed-loop review actions")

if "alarm_silenced" not in st.session_state:
    st.session_state.alarm_silenced = {}
if "alarm_acked" not in st.session_state:
    st.session_state.alarm_acked = {}

raw_df = st.session_state.active_df
alerts = detect_alerts_from_dataframe(raw_df)

if not alerts:
    st.info("No active surveillance alerts in current dataset.")
    st.stop()

# Reliable High-Priority Alarm Banner
high_alerts = [a for a in alerts if a.severity in ("Critical", "High")]
if high_alerts:
    top_high = high_alerts[0]
    is_silenced = st.session_state.alarm_silenced.get(top_high.id, False) or top_high.id in GLOBAL_ALARM_MANAGER.silenced_alert_ids
    is_acked = st.session_state.alarm_acked.get(top_high.id, False) or top_high.id in GLOBAL_ALARM_MANAGER.acknowledged_alert_ids or st.session_state.alert_reviews.get(top_high.id, {}).get("status") in ["Resolved / False Anomaly", "Reviewed", "Acknowledged"]

    alarm_status = "ACKNOWLEDGED" if is_acked else ("SILENCED" if is_silenced else "ALARM SOUNDING")
    status_bg = "#10B981" if is_acked else ("#F59E0B" if is_silenced else "#EF4444")
    status_icon = "✔" if is_acked else ("🔇" if is_silenced else "🔊")

    st.markdown(
        f"""
        <div style="background: rgba(239, 68, 68, 0.12); border: 2px solid #EF4444; border-radius: 10px; padding: 14px 18px; margin-bottom: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 24px;">🚨</span>
                    <div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <strong style="color: #FFFFFF; font-size: 1.05rem;">HIGH-PRIORITY SURVEILLANCE ALARM: {top_high.id}</strong>
                            <span style="background: {status_bg}; color: #FFFFFF; font-size: 0.72rem; font-weight: 800; padding: 3px 8px; border-radius: 12px; letter-spacing: 0.5px;">
                                {status_icon} {alarm_status}
                            </span>
                        </div>
                        <div style="color: #CBD5E1; font-size: 0.85rem; margin-top: 2px;">
                            Surveillance Signal: <strong>{top_high.organism} vs {top_high.antibiotic}</strong> in <strong>{top_high.department}</strong>
                            (Observed: <strong style="color:#EF4444;">{top_high.current_rate:.1f}%</strong> vs Baseline: {top_high.baseline_rate:.1f}%, Shift: {top_high.pct_point_change:+.1f} pp, N={top_high.current_tested})
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    bcol1, bcol2, bcol3, bcol4 = st.columns([1.2, 1.2, 1.2, 2])
    with bcol1:
        if st.button("⏹ STOP ALARM", key="btn_stop_alarm", help="Immediately silence alarm sound without dismissing alert", use_container_width=True):
            st.session_state.alarm_silenced[top_high.id] = True
            GLOBAL_ALARM_MANAGER.stop_alarm(top_high.id)
            st.toast("Alarm sound stopped immediately. Alert remains active in surveillance.", icon="🔇")
            st.rerun()
    with bcol2:
        if st.button("✔ ACKNOWLEDGE", key="btn_ack_alarm", help="Acknowledge alert and log review", use_container_width=True):
            st.session_state.alarm_acked[top_high.id] = True
            st.session_state.alarm_silenced[top_high.id] = True
            GLOBAL_ALARM_MANAGER.acknowledge_alert(top_high.id)
            st.toast(f"Alert {top_high.id} acknowledged.", icon="✔")
            st.rerun()
    with bcol3:
        if st.button("🔊 TEST SOUND", key="btn_test_sound", help="Test medical alarm siren", use_container_width=True):
            st.components.v1.html(
                """
                <script>
                try {
                  const ctx = new (window.AudioContext || window.webkitAudioContext)();
                  const osc = ctx.createOscillator();
                  const gain = ctx.createGain();
                  osc.frequency.setValueAtTime(880, ctx.currentTime);
                  gain.gain.setValueAtTime(0.15, ctx.currentTime);
                  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
                  osc.connect(gain);
                  gain.connect(ctx.destination);
                  osc.start();
                  osc.stop(ctx.currentTime + 0.3);
                } catch(e) {}
                </script>
                """,
                height=0,
                width=0
            )
            st.toast("Playing test alarm beep...", icon="🔊")
    with bcol4:
        st.caption("Surveillance priority alarm triggers only on valid high/critical alerts with N ≥ 15.")

# Alert Selector
alert_map = {f"[{a.severity}] {a.id} — {a.organism} vs {a.antibiotic} ({a.department})": a.id for a in alerts}
alert_labels = list(alert_map.keys())

# Default selection
curr_sel_id = st.session_state.get("selected_alert_id", alerts[0].id)
default_idx = 0
for idx, lbl in enumerate(alert_labels):
    if alert_map[lbl] == curr_sel_id:
        default_idx = idx
        break

selected_label = st.selectbox("Select Signal to Investigate", alert_labels, index=default_idx)
selected_alert_id = alert_map[selected_label]
st.session_state.selected_alert_id = selected_alert_id

selected_alert = next((a for a in alerts if a.id == selected_alert_id), alerts[0])

# Severity & Overview
sev_class = f"badge-{selected_alert.severity.lower()}"
st.markdown(
    f"""
    <div class="amr-card" style="border-left: 4px solid {ACCENT_TEAL};">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span class="{sev_class}">{selected_alert.severity.upper()}</span>
                <h2 style="margin: 8px 0 4px 0; font-size: 1.4rem;">{selected_alert.title}</h2>
                <div style="color: {TEXT_MUTED}; font-size: 0.9rem;">
                    Signal ID: <strong>{selected_alert.id}</strong> · Unit: <strong>{selected_alert.department}</strong>
                </div>
            </div>
            <div>
                <span style="font-size: 0.85rem; color: {TEXT_MUTED};">Current Triage Status:</span>
                <span style="font-weight: 600; color: #FFFFFF; background: {BORDER_DARK}; padding: 4px 10px; border-radius: 4px; margin-left: 6px;">
                    {st.session_state.alert_reviews.get(selected_alert.id, {}).get('status', selected_alert.status)}
                </span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Evidence Breakdown Row
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        f"""
        <div class="amr-card">
            <div class="kpi-title">Current Window Resistance</div>
            <div class="kpi-val">{selected_alert.current_rate:.1f}%</div>
            <div class="kpi-sub">Resistant: {selected_alert.current_resistant} / Tested: {selected_alert.current_tested}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        f"""
        <div class="amr-card">
            <div class="kpi-title">Baseline Window Resistance</div>
            <div class="kpi-val">{selected_alert.baseline_rate:.1f}%</div>
            <div class="kpi-sub">Resistant: {selected_alert.baseline_resistant} / Tested: {selected_alert.baseline_tested}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:
    st.markdown(
        f"""
        <div class="amr-card">
            <div class="kpi-title">Percentage-Point Surge</div>
            <div class="kpi-val" style="color: {ACCENT_TEAL};">{selected_alert.pct_point_change:+.1f}% pt</div>
            <div class="kpi-sub">Epidemiological rate difference</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# Rule Details & Caveats
rule_col, trend_col = st.columns([1.2, 1])

with rule_col:
    st.subheader("📋 10-Point Epidemiological Evidence Panel")
    ev = selected_alert.evidence or {}

    st.markdown(
        """
        <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 6px; padding: 8px 12px; margin-bottom: 10px; font-size: 0.8rem; color: #F59E0B;">
            ⚠️ <strong>SURVEILLANCE SIGNAL FOR INVESTIGATION:</strong> Automated algorithmic detection based on verified AST records. Not a confirmed hospital outbreak or clinical treatment mandate.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <div style="display: flex; flex-direction: column; gap: 8px; font-size: 0.85rem;">
            <div style="background: #111C38; border: 1px solid #1E2D5A; border-radius: 6px; padding: 8px 12px;">
                <span style="color:#00E5FF; font-weight:700; font-size:0.75rem; text-transform:uppercase;">1. What Was Detected</span>
                <div style="color:#FFFFFF; font-weight:600; margin-top:2px;">{ev.get('what_detected', selected_alert.title)}</div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                <div style="background: #111C38; border: 1px solid #1E2D5A; border-radius: 6px; padding: 8px 12px;">
                    <span style="color:#00E5FF; font-weight:700; font-size:0.75rem; text-transform:uppercase;">2. Organism & Antibiotic</span>
                    <div style="color:#FFFFFF; margin-top:2px;"><em>{selected_alert.organism}</em> × {selected_alert.antibiotic}</div>
                </div>
                <div style="background: #111C38; border: 1px solid #1E2D5A; border-radius: 6px; padding: 8px 12px;">
                    <span style="color:#00E5FF; font-weight:700; font-size:0.75rem; text-transform:uppercase;">3. Location & Periods</span>
                    <div style="color:#CBD5E1; margin-top:2px;">{ev.get('location_and_time', f'Unit: {selected_alert.department}')}</div>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                <div style="background: #111C38; border: 1px solid #1E2D5A; border-radius: 6px; padding: 8px 12px;">
                    <span style="color:#00E5FF; font-weight:700; font-size:0.75rem; text-transform:uppercase;">4. Observed Resistance</span>
                    <div style="color:#EF4444; font-weight:700; font-size:1.05rem; margin-top:2px;">{selected_alert.current_rate:.1f}%</div>
                    <div style="color:#94A3B8; font-size:0.75rem;">Formula: ({selected_alert.current_resistant} / {selected_alert.current_tested} tested)</div>
                </div>
                <div style="background: #111C38; border: 1px solid #1E2D5A; border-radius: 6px; padding: 8px 12px;">
                    <span style="color:#00E5FF; font-weight:700; font-size:0.75rem; text-transform:uppercase;">5. Comparison Baseline</span>
                    <div style="color:#FFFFFF; font-weight:700; font-size:1.05rem; margin-top:2px;">{selected_alert.baseline_rate:.1f}%</div>
                    <div style="color:#94A3B8; font-size:0.75rem;">Formula: ({selected_alert.baseline_resistant} / {selected_alert.baseline_tested} tested)</div>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                <div style="background: #111C38; border: 1px solid #1E2D5A; border-radius: 6px; padding: 8px 12px;">
                    <span style="color:#00E5FF; font-weight:700; font-size:0.75rem; text-transform:uppercase;">6. Epidemiological Delta</span>
                    <div style="color:#F59E0B; font-weight:700; font-size:1.05rem; margin-top:2px;">{selected_alert.pct_point_change:+.1f} pp</div>
                    <div style="color:#94A3B8; font-size:0.75rem;">Percentage-point difference</div>
                </div>
                <div style="background: #111C38; border: 1px solid #1E2D5A; border-radius: 6px; padding: 8px 12px;">
                    <span style="color:#00E5FF; font-weight:700; font-size:0.75rem; text-transform:uppercase;">7. Sample Size Breakdown</span>
                    <div style="color:#CBD5E1; margin-top:2px;">Current: N={selected_alert.current_tested} | Baseline: N={selected_alert.baseline_tested}</div>
                </div>
            </div>
            <div style="background: #111C38; border: 1px solid #1E2D5A; border-radius: 6px; padding: 8px 12px;">
                <span style="color:#00E5FF; font-weight:700; font-size:0.75rem; text-transform:uppercase;">8. Deterministic Trigger Rule</span>
                <div style="color:#EF4444; font-weight:600; margin-top:2px;">{ev.get('trigger_rule', selected_alert.trigger_reason)}</div>
            </div>
            <div style="background: #111C38; border: 1px solid #1E2D5A; border-radius: 6px; padding: 8px 12px;">
                <span style="color:#00E5FF; font-weight:700; font-size:0.75rem; text-transform:uppercase;">9. Data Quality & Limitations</span>
                <div style="color:#CBD5E1; margin-top:2px;">{ev.get('data_quality', selected_alert.caveats or 'CLSI M100 compliant AST records with zero schema quarantine exclusions.')}</div>
            </div>
            <div style="background: #0F243A; border: 1px solid #0284C7; border-radius: 6px; padding: 8px 12px;">
                <span style="color:#38BDF8; font-weight:700; font-size:0.75rem; text-transform:uppercase;">10. Recommended Next Step</span>
                <div style="color:#E0F2FE; margin-top:2px;">{ev.get('recommended_next_step', 'Assign authorized analyst to review isolate cultures, audit ICU prescriptions, and alert IPC committee.')}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("")
    if st.button("🤖 Ask AI Copilot to Explain This Alert", use_container_width=True):
        st.session_state.selected_alert_id = selected_alert.id
        st.switch_page("pages/4_AI_Copilot.py")

with trend_col:
    st.subheader("📈 Signal-Specific Trajectory")
    sig_df = raw_df[
        (raw_df["organism"] == selected_alert.organism) &
        (raw_df["antibiotic"] == selected_alert.antibiotic) &
        (raw_df["department"] == selected_alert.department)
    ].copy()
    
    if not sig_df.empty:
        sig_df["year_month"] = pd.to_datetime(sig_df["test_date"]).dt.to_period("M").astype(str)
        pts = []
        for ym, grp in sig_df.groupby("year_month"):
            r = calculate_resistance_rate(grp, min_denominator=1)
            pts.append({"Month": ym, "Rate": r.resistance_rate or 0})
        
        sig_trend = pd.DataFrame(pts)
        if not sig_trend.empty:
            fig = go.Figure(go.Scatter(
                x=sig_trend["Month"],
                y=sig_trend["Rate"],
                mode="lines+markers",
                line=dict(color="#EF4444" if selected_alert.severity in ["Critical", "High"] else ACCENT_TEAL, width=3),
                marker=dict(size=8, color="#FFFFFF")
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(17, 24, 39, 0.7)",
                margin=dict(l=10, r=10, t=10, b=10),
                yaxis=dict(range=[0, 100], gridcolor=BORDER_DARK, title="Rate (%)"),
                font=dict(color="#D1D5DB"),
                height=240,
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No historical granular data points for this specific slice.")

st.markdown("---")

# Closed-Loop Review & Decision Form
st.subheader("✍️ Human-in-the-Loop Clinical Triage & Decision Audit")

from src.auth import has_permission
curr_user = st.session_state.get("authenticated_user")
curr_role = curr_user.get("role", "viewer") if curr_user else "viewer"
can_triage = has_permission(curr_role, "can_acknowledge_alerts")

review_data = st.session_state.alert_reviews.get(selected_alert.id, {})
status_opts = ["Active", "Under Review", "Escalated to IPC Committee", "Resolved / False Anomaly"]
curr_st = review_data.get("status", selected_alert.status)
idx_st = status_opts.index(curr_st) if curr_st in status_opts else 0

if not can_triage:
    st.info("🔒 **Read-Only Access Mode**: Alert status triage and decision recording are restricted to Surveillance Analysts and System Administrators.")
    st.write(f"**Current Status:** `{curr_st}` | **Assigned To:** `{review_data.get('assigned_to', 'Dr. A. Sharma (IPC Lead)')}`")
    st.write(f"**Notes:** {review_data.get('notes', 'Reviewed ICU isolate records.')}")
else:
    col_act1, col_act2 = st.columns([1, 2])

    with col_act1:
        new_status = st.selectbox("Update Triage Status", status_opts, index=idx_st)
        assigned_to = st.text_input("Investigating Clinician / Epidemiologist", value=review_data.get("assigned_to", "Dr. A. Sharma (IPC Lead)"))

    with col_act2:
        notes = st.text_area("Investigation Notes & Verification Actions", value=review_data.get("notes", "Reviewed ICU isolate records. Ordered environmental swab testing for ICU bay 3 and re-checked automated VITEK-2 testing panel lots."))

    if st.button("💾 Save Clinical Decision & Update Audit Trail", type="primary"):
        st.session_state.alert_reviews[selected_alert.id] = {
            "status": new_status,
            "assigned_to": assigned_to,
            "notes": notes,
            "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        st.success(f"Audit decision saved for {selected_alert.id}: Status marked as '{new_status}'.")
        st.rerun()
