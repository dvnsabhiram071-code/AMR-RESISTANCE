"""
AMR Sentinel - System Administration, Role Management & Audit Console (pages/8_Admin_Console.py)
Restricted exclusively to users with the 'admin' role.
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from src.ui_helpers import (
    initialize_session_state,
    render_header,
    PANEL_BG,
    ACCENT_TEAL,
    BORDER_DARK,
    TEXT_MUTED
)
from src.auth import (
    load_users,
    save_users,
    get_audit_logs,
    has_permission,
    ROLE_SYSTEM_ADMIN,
    ROLE_SURVEILLANCE_ANALYST,
    ROLE_READ_ONLY_VIEWER,
    ROLE_NAMES,
    hash_password,
    validate_password_policy,
    audit_log_event
)

st.set_page_config(page_title="AMR Sentinel · Admin Console", page_icon="⚙️", layout="wide")
initialize_session_state()

# 1. Server-side Authentication & Permission Check
current_user = st.session_state.get("authenticated_user")

if not current_user:
    st.error("🔒 Authentication required. Please sign in to access the Administration Console.")
    if st.button("👉 Go to Sign In", type="primary"):
        st.session_state.auth_view = "login"
        st.switch_page("app.py")
    st.stop()

if not has_permission(current_user.get("role", ""), "can_manage_users"):
    st.error(f"⛔ Access Denied: Your assigned role ({ROLE_NAMES.get(current_user.get('role'), current_user.get('role'))}) does not have permission to manage users or access the Administration Console.")
    st.info("Surveillance Analysts and Read-Only Viewers are restricted from system configuration. Please contact your System Administrator.")
    st.stop()

render_header("System Administration & Security Console", "Manage role-based user accounts, review security audit logs, and inspect platform status")

tab_users, tab_audit, tab_system = st.tabs(["👥 User Accounts & Roles", "📜 Security Audit Log", "🖥️ System Status & Config"])

# ========================================================
# TAB 1: User Accounts & Roles
# ========================================================
with tab_users:
    st.subheader("Registered Surveillance User Directory")
    users = load_users()

    user_rows = []
    for email, u in users.items():
        user_rows.append({
            "Email Address": u.get("email"),
            "Display Name": u.get("name"),
            "Role": ROLE_NAMES.get(u.get("role"), u.get("role")),
            "Temporary Pwd": "⚠️ Required" if u.get("must_change_password") else "✓ Updated",
            "Last Login": u.get("last_login") or "Never",
            "Created Date": (u.get("created_at") or "")[:10]
        })

    df_users = pd.DataFrame(user_rows)
    st.dataframe(df_users, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("➕ Provision New User Account")

    with st.form("create_user_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_email = st.text_input("User Email Address", placeholder="e.g. epidemiologist@hospital.org")
            new_name = st.text_input("Full Display Name", placeholder="e.g. Dr. Alex Mercer")
        with col2:
            new_role = st.selectbox(
                "Role Assignment",
                options=[ROLE_SURVEILLANCE_ANALYST, ROLE_READ_ONLY_VIEWER, ROLE_SYSTEM_ADMIN],
                format_func=lambda r: f"{ROLE_NAMES.get(r, r)} ({r})"
            )
            new_temp_pwd = st.text_input("Temporary Initial Password", placeholder="Min 12 characters", type="password")

        force_pwd_change = st.checkbox("Require password change on first login", value=True)
        submit_user = st.form_submit_button("Provision User", type="primary")

        if submit_user:
            if not new_email or not new_temp_pwd:
                st.error("Email and initial password are required.")
            elif new_email.lower() in [k.lower() for k in users.keys()]:
                st.error(f"User account {new_email} already exists.")
            else:
                is_valid, errors = validate_password_policy(new_temp_pwd)
                if not is_valid:
                    st.error("Temporary password does not meet security requirements: " + " ".join(errors))
                else:
                    pwd_hash, pwd_salt = hash_password(new_temp_pwd)
                    now_str = datetime.now().isoformat()
                    users[new_email.lower()] = {
                        "email": new_email.lower(),
                        "name": new_name or new_email.split("@")[0],
                        "password_hash": pwd_hash,
                        "salt": pwd_salt,
                        "role": new_role,
                        "must_change_password": force_pwd_change,
                        "created_at": now_str,
                        "last_login": None
                    }
                    save_users(users)
                    audit_log_event("USER_PROVISIONED", current_user["email"], f"Created new {new_role} account for {new_email}")
                    st.success(f"User {new_email} provisioned successfully with role {ROLE_NAMES.get(new_role)}!")
                    st.rerun()

# ========================================================
# TAB 2: Security Audit Log
# ========================================================
with tab_audit:
    st.subheader("Security & Access Audit Trail")
    st.caption("Immutable record of system bootstrap, authentication events, password changes, and administrative actions.")

    logs = get_audit_logs()
    if logs:
        df_logs = pd.DataFrame(logs)[::-1] # Reverse chronological
        st.dataframe(df_logs, use_container_width=True, hide_index=True)
    else:
        st.info("No audit log events recorded yet.")

# ========================================================
# TAB 3: System Status & Config
# ========================================================
with tab_system:
    st.subheader("Platform Health & Security Configuration")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown(
            f"""
            <div class="amr-card">
                <h4 style="margin-top:0; color:#FFFFFF;">Authentication Engine</h4>
                <ul style="color:#D1D5DB; font-size:0.9rem; line-height:1.8;">
                    <li>Hashing Algorithm: <strong>PBKDF2-HMAC-SHA256 (100,000 rounds)</strong></li>
                    <li>Salt Generation: <strong>Cryptographically secure 16-byte CSPRNG</strong></li>
                    <li>Policy Enforcement: <strong>&ge; 12 chars, upper, lower, digit, symbol</strong></li>
                    <li>First-Login Enforcement: <strong>Server-side must_change_password flag</strong></li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_s2:
        st.markdown(
            f"""
            <div class="amr-card">
                <h4 style="margin-top:0; color:#FFFFFF;">Active Surveillance Dataset</h4>
                <ul style="color:#D1D5DB; font-size:0.9rem; line-height:1.8;">
                    <li>Dataset Scenario: <strong>{st.session_state.get('scenario_name', 'Default')}</strong></li>
                    <li>Active AST Isolates: <strong>{len(st.session_state.get('active_df', [])):,} records</strong></li>
                    <li>Surveillance Status: <strong>Prototypic Synthetic Demonstration</strong></li>
                    <li>Clinical Advisory: <strong>Non-diagnostic, academic research only</strong></li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )
