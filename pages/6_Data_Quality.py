"""
AMR Sentinel - Data Quality, Ingestion & Quarantine Audit
"""
import streamlit as st
import pandas as pd
import io

from src.ui_helpers import (
    initialize_session_state,
    render_header,
    require_authentication,
    ACCENT_TEAL,
    BORDER_DARK,
    PANEL_BG,
    TEXT_MUTED
)
from src.validation import validate_and_clean_amr_data
from src.scenarios import load_scenario_dataset
from src.alerts import detect_alerts_from_dataframe

st.set_page_config(page_title="AMR Sentinel · Data Quality", page_icon="🛡️", layout="wide")
initialize_session_state()
require_authentication()
render_header("Data Quality & Ingestion Audit", "Verify schema compliance, monitor quarantined rows, and upload laboratory AST records")

report = st.session_state.validation_report

# 1. Quality KPI Metrics
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        f"""
        <div class="amr-card">
            <div class="kpi-title">Total Records Ingested</div>
            <div class="kpi-val">{report.total_rows:,}</div>
            <div class="kpi-sub">Source dataset rows</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with c2:
    valid_pct = (report.valid_rows / report.total_rows * 100) if report.total_rows > 0 else 0
    st.markdown(
        f"""
        <div class="amr-card">
            <div class="kpi-title">Accepted Valid Records</div>
            <div class="kpi-val" style="color: #10B981;">{report.valid_rows:,}</div>
            <div class="kpi-sub">{valid_pct:.1f}% acceptance rate</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with c3:
    st.markdown(
        f"""
        <div class="amr-card">
            <div class="kpi-title">Quarantined / Excluded</div>
            <div class="kpi-val" style="color: {'#EF4444' if report.excluded_rows > 0 else '#10B981'};">{report.excluded_rows:,}</div>
            <div class="kpi-sub">Schema & quality violations</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with c4:
    date_cov = f"{report.date_min} to {report.date_max}" if report.date_min else "N/A"
    st.markdown(
        f"""
        <div class="amr-card">
            <div class="kpi-title">Date Coverage</div>
            <div class="kpi-val" style="font-size: 1.1rem; padding-top: 8px;">{date_cov}</div>
            <div class="kpi-sub">Surveillance temporal span</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")

# 2. Detailed Quality Breakdown
st.subheader("🔍 Schema Conformance Breakdown")
col_b1, col_b2 = st.columns(2)

with col_b1:
    st.markdown(
        f"""
        <div class="amr-card">
            <h4 style="margin-top: 0; color: #FFFFFF;">Integrity Violations</h4>
            <ul style="color: #D1D5DB; font-size: 0.95rem; line-height: 1.8;">
                <li>Duplicate records detected: <strong>{report.duplicate_count}</strong></li>
                <li>Invalid S/I/R category values: <strong>{report.invalid_category_count}</strong></li>
                <li>Unparseable date formats: <strong>{report.invalid_date_count}</strong></li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_b2:
    st.markdown(
        f"""
        <div class="amr-card">
            <h4 style="margin-top: 0; color: #FFFFFF;">Missing Field Counts</h4>
            <ul style="color: #D1D5DB; font-size: 0.95rem; line-height: 1.8;">
                {"".join([f"<li>{col}: <strong>{cnt}</strong> missing</li>" for col, cnt in report.missing_values.items() if cnt > 0]) or "<li>None. All required fields populated!</li>"}
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )

# 3. Quarantined Records Table
if report.excluded_rows > 0:
    st.subheader("⚠️ Quarantined Records & Rejection Explanations")
    st.dataframe(
        report.excluded_df,
        use_container_width=True,
        hide_index=True
    )
else:
    st.success("✅ Clean dataset. Zero records quarantined.")

st.markdown("---")

# 4. Upload New Dataset or Restore
st.subheader("📤 Laboratory CSV Ingestion & Dataset Switching")

upload_col, restore_col = st.columns([2, 1])

with upload_col:
    from src.auth import has_permission
    curr_user = st.session_state.get("authenticated_user")
    curr_role = curr_user.get("role", "viewer") if curr_user else "viewer"
    can_upload = has_permission(curr_role, "can_upload_ast_data")

    if not can_upload:
        st.info("🔒 **Read-Only Access Mode**: AST CSV upload and ingestion are restricted to Surveillance Analysts and System Administrators.")
    else:
        uploaded_file = st.file_uploader(
            "Upload Microbiology Laboratory CSV",
            type=["csv"],
            help="Upload an authorized, de-identified AST export. Maximum file size: 15MB."
        )
        if uploaded_file is not None:
            try:
                raw_upload_df = pd.read_csv(uploaded_file)
                new_report = validate_and_clean_amr_data(raw_upload_df)
                
                # Show preview before accepting
                st.markdown(f"**Previewing:** `{uploaded_file.name}` ({new_report.valid_rows:,} valid rows, {new_report.excluded_rows:,} quarantined)")
                if st.button("📥 Apply Uploaded Dataset to Active Surveillance", type="primary"):
                    st.session_state.validation_report = new_report
                    st.session_state.active_df = new_report.clean_df
                    st.session_state.scenario_name = f"Uploaded File ({uploaded_file.name})"
                    st.session_state.alerts_cache = detect_alerts_from_dataframe(new_report.clean_df)
                    st.success(f"Successfully loaded {new_report.valid_rows:,} valid records from {uploaded_file.name}!")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Upload validation failed: {str(e)}")

with restore_col:
    st.markdown("#### One-Click Recovery")
    st.caption("Restore the pristine synthetic demonstration baseline dataset.")
    if st.button("🔄 Reset to Synthetic Demo Data", use_container_width=True):
        report, s_name = load_scenario_dataset(scenario_key="sudden_spike")
        st.session_state.validation_report = report
        st.session_state.active_df = report.clean_df
        st.session_state.scenario_name = s_name
        st.session_state.scenario_key = "sudden_spike"
        st.session_state.alerts_cache = detect_alerts_from_dataframe(report.clean_df)
        st.success("Restored synthetic demo dataset!")
        st.rerun()
