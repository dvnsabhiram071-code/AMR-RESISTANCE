"""
Shared UI Utilities, CSS Styling, and State Management for AMR Sentinel.
"""
import os
import streamlit as st
import pandas as pd
from typing import Tuple, Dict, Any, List, Optional
from src.scenarios import load_scenario_dataset, SCENARIOS
from src.alerts import detect_alerts_from_dataframe, AMRAlert
from src.metrics import calculate_resistance_rate


NAVY_BG = "#0B1220"
PANEL_BG = "#111827"
ACCENT_TEAL = "#14B8A6"
TEXT_LIGHT = "#F3F4F6"
TEXT_MUTED = "#9CA3AF"
BORDER_DARK = "#1F2937"


def apply_custom_theme():
    """Injects consistent navy & teal clinical dashboard styling."""
    st.markdown(
        f"""
        <style>
            /* Main container styling */
            .stApp {{
                background-color: {NAVY_BG};
                color: {TEXT_LIGHT};
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            }}

            /* Headers */
            h1, h2, h3, h4 {{
                color: #FFFFFF !important;
                font-weight: 600;
            }}

            /* Cards */
            .amr-card {{
                background-color: {PANEL_BG};
                border: 1px solid {BORDER_DARK};
                border-radius: 8px;
                padding: 18px 22px;
                margin-bottom: 16px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
            }}

            .kpi-title {{
                font-size: 0.85rem;
                font-weight: 500;
                color: {TEXT_MUTED};
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: 6px;
            }}

            .kpi-val {{
                font-size: 2rem;
                font-weight: 700;
                color: #FFFFFF;
                line-height: 1.1;
            }}

            .kpi-sub {{
                font-size: 0.8rem;
                color: {ACCENT_TEAL};
                margin-top: 6px;
            }}

            /* Synthetic demo data badge */
            .synthetic-badge {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                background-color: rgba(245, 158, 11, 0.15);
                color: #F59E0B;
                border: 1px solid rgba(245, 158, 11, 0.4);
                padding: 4px 12px;
                border-radius: 9999px;
                font-size: 0.75rem;
                font-weight: 600;
                letter-spacing: 0.05em;
                margin-bottom: 12px;
            }}

            /* Severity Badges */
            .badge-critical {{
                background-color: rgba(239, 68, 68, 0.2);
                color: #EF4444;
                border: 1px solid #EF4444;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.75rem;
                font-weight: 600;
            }}
            .badge-high {{
                background-color: rgba(249, 115, 22, 0.2);
                color: #F97316;
                border: 1px solid #F97316;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.75rem;
                font-weight: 600;
            }}
            .badge-moderate {{
                background-color: rgba(245, 158, 11, 0.2);
                color: #F59E0B;
                border: 1px solid #F59E0B;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.75rem;
                font-weight: 600;
            }}
            .badge-watch {{
                background-color: rgba(20, 184, 166, 0.2);
                color: #14B8A6;
                border: 1px solid #14B8A6;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.75rem;
                font-weight: 600;
            }}

            /* Streamlit widgets overrides */
            div[data-baseweb="select"] > div {{
                background-color: {PANEL_BG} !important;
                border-color: {BORDER_DARK} !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_session_state():
    """Initializes app session state and loads base scenario dataset."""
    if "scenario_key" not in st.session_state:
        st.session_state.scenario_key = "sudden_spike"

    if "validation_report" not in st.session_state or "raw_df" not in st.session_state:
        demo_csv = os.path.join(os.path.dirname(__file__), "..", "data", "demo_isolates.csv")
        # Try loading initial scenario
        report, scenario_name = load_scenario_dataset(
            scenario_key=st.session_state.scenario_key,
            demo_csv_path=demo_csv
        )
        st.session_state.validation_report = report
        st.session_state.active_df = report.clean_df
        st.session_state.scenario_name = scenario_name

    if "alerts_cache" not in st.session_state:
        st.session_state.alerts_cache = detect_alerts_from_dataframe(st.session_state.active_df)

    if "selected_alert_id" not in st.session_state:
        st.session_state.selected_alert_id = (
            st.session_state.alerts_cache[0].id if st.session_state.alerts_cache else None
        )

    if "alert_reviews" not in st.session_state:
        st.session_state.alert_reviews = {}


def render_header(title: str, subtitle: str = ""):
    """Renders consistent top status row with persistent synthetic badge."""
    apply_custom_theme()
    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 18px;">
            <div>
                <h1 style="margin: 0; font-size: 1.85rem; color: #FFFFFF;">🛡️ AMR Sentinel · {title}</h1>
                <p style="margin: 4px 0 0 0; color: {TEXT_MUTED}; font-size: 0.92rem;">{subtitle}</p>
            </div>
            <div style="text-align: right;">
                <span class="synthetic-badge">⚠️ SYNTHETIC DEMO DATA · NOT FOR CLINICAL USE</span>
                <div style="font-size: 0.75rem; color: {TEXT_MUTED}; margin-top: 4px;">
                    Scenario: <strong style="color: {ACCENT_TEAL};">{st.session_state.get('scenario_name', 'Active')}</strong>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_filters(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Renders the standard global filters in the sidebar and returns filtered df."""
    render_sidebar_auth()
    st.sidebar.markdown(f"### 🔍 Surveillance Filters")

    if df is None or df.empty:
        return df, {}

    # Department filter
    dept_opts = ["All Departments"] + sorted([str(d) for d in df["department"].dropna().unique()])
    sel_dept = st.sidebar.selectbox("Department / Ward", dept_opts, index=0)

    # Organism filter
    org_opts = ["All Organisms"] + sorted([str(o) for o in df["organism"].dropna().unique()])
    sel_org = st.sidebar.selectbox("Pathogen / Organism", org_opts, index=0)

    # Antibiotic filter
    abx_opts = ["All Antimicrobials"] + sorted([str(a) for a in df["antibiotic"].dropna().unique()])
    sel_abx = st.sidebar.selectbox("Antimicrobial Agent", abx_opts, index=0)

    # Date range filter
    min_date = pd.to_datetime(df["test_date"]).min().date()
    max_date = pd.to_datetime(df["test_date"]).max().date()

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    if st.sidebar.button("Reset Filters", use_container_width=True):
        st.rerun()

    # Apply filters
    filtered_df = df.copy()

    if sel_dept != "All Departments":
        filtered_df = filtered_df[filtered_df["department"] == sel_dept]

    if sel_org != "All Organisms":
        filtered_df = filtered_df[filtered_df["organism"] == sel_org]

    if sel_abx != "All Antimicrobials":
        filtered_df = filtered_df[filtered_df["antibiotic"] == sel_abx]

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_d, end_d = date_range
        filtered_df = filtered_df[
            (filtered_df["test_date"] >= start_d.strftime("%Y-%m-%d")) &
            (filtered_df["test_date"] <= end_d.strftime("%Y-%m-%d"))
        ]

    filter_meta = {
        "department": sel_dept,
        "organism": sel_org,
        "antibiotic": sel_abx,
        "date_range": f"{date_range[0]} to {date_range[1]}" if isinstance(date_range, tuple) and len(date_range) == 2 else "All",
    }

    return filtered_df, filter_meta


def get_current_user() -> Optional[Dict[str, Any]]:
    """Returns the currently authenticated user dictionary or None."""
    return st.session_state.get("authenticated_user", None)


def is_authenticated() -> bool:
    """Returns True if a user is currently authenticated."""
    return get_current_user() is not None


def require_authentication() -> bool:
    """
    Guard for Streamlit pages. Displays a clean sign-in prompt and halts page execution
    if the session is unauthenticated or has not changed their temporary password.
    """
    user = get_current_user()
    if not user:
        apply_custom_theme()
        st.warning("🔒 Authentication required. Please sign in to access this surveillance page.")
        if st.button("👉 Sign In", type="primary"):
            st.session_state.auth_view = "login"
            st.switch_page("app.py")
        st.stop()
        return False
    if user.get("must_change_password"):
        apply_custom_theme()
        st.warning("⚠️ Security policy requires setting a permanent password before accessing surveillance features.")
        if st.button("👉 Set Permanent Password", type="primary"):
            st.session_state.auth_view = "change_password"
            st.switch_page("app.py")
        st.stop()
        return False
    return True


def render_sidebar_auth():
    """Renders the user profile card and role badge at the top of the Streamlit sidebar."""
    user = get_current_user()
    if user:
        role_label = user.get("role", "viewer").capitalize()
        role_colors = {
            "admin": ("#EF4444", "rgba(239, 68, 68, 0.15)"),
            "analyst": ("#00E5FF", "rgba(0, 229, 255, 0.15)"),
            "viewer": ("#38BDF8", "rgba(56, 189, 248, 0.15)"),
        }
        text_color, bg_color = role_colors.get(user.get("role", "viewer"), ("#94A3B8", "rgba(148, 163, 184, 0.15)"))

        st.sidebar.markdown(
            f"""
            <div style="background: #111C38; border: 1px solid #1E2D5A; border-radius: 8px; padding: 12px; margin-bottom: 14px;">
                <div style="font-size: 0.75rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.5px;">Logged in as</div>
                <div style="font-weight: 700; color: #FFFFFF; font-size: 0.95rem; margin: 2px 0;">{user.get('name', user.get('email'))}</div>
                <div style="display: inline-block; background: {bg_color}; color: {text_color}; border: 1px solid {text_color}; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; margin-top: 4px;">
                    {role_label}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.sidebar.button("🚪 Sign Out", key="sidebar_sign_out_btn", use_container_width=True):
            st.session_state.authenticated_user = None
            st.session_state.auth_view = "landing"
            st.rerun()

