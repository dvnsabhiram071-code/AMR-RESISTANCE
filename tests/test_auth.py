"""
Unit tests for AMR Sentinel role-based authentication, password policy, and permissions.
"""
import os
import json
import pytest
from src.auth import (
    hash_password,
    verify_password,
    validate_password_policy,
    authenticate_user,
    change_user_password,
    has_permission,
    get_audit_logs,
    load_users,
    initialize_default_users,
    ROLE_SYSTEM_ADMIN,
    ROLE_SURVEILLANCE_ANALYST,
    ROLE_READ_ONLY_VIEWER,
    USERS_FILE
)


@pytest.fixture(autouse=True)
def reset_user_database():
    """Ensure a fresh default database state for each test."""
    initialize_default_users(reset_passwords=True)
    yield
    initialize_default_users(reset_passwords=True)


def test_password_hashing():
    pwd = "TemporarySecret#123"
    h1, s1 = hash_password(pwd)
    h2, s2 = hash_password(pwd)
    
    # Different salts must yield different hashes
    assert s1 != s2
    assert h1 != h2
    assert verify_password(pwd, h1, s1) is True
    assert verify_password(pwd, h2, s2) is True
    assert verify_password("WrongPassword", h1, s1) is False


def test_password_policy():
    # Too short (< 12)
    valid, errors = validate_password_policy("Short@123")
    assert valid is False
    assert any("at least 12 characters" in e for e in errors)

    # Missing uppercase
    valid, errors = validate_password_policy("lowercase_only@123")
    assert valid is False
    assert any("uppercase" in e for e in errors)

    # Missing lowercase
    valid, errors = validate_password_policy("UPPERCASE_ONLY@123")
    assert valid is False
    assert any("lowercase" in e for e in errors)

    # Missing number
    valid, errors = validate_password_policy("NoNumbersHere!@#$")
    assert valid is False
    assert any("number" in e for e in errors)

    # Missing special character
    valid, errors = validate_password_policy("NoSpecialChar12345")
    assert valid is False
    assert any("special character" in e for e in errors)

    # Fully valid password
    valid, errors = validate_password_policy("CompliantPass#2026")
    assert valid is True
    assert len(errors) == 0


def test_three_bootstrap_accounts_initialized_with_temporary_credentials():
    # 1. Surveillance Analyst account
    s1, u1, _ = authenticate_user("dvnsabhiram071@gmail.com", "Abhi@071", selected_role="analyst")
    assert s1 is True
    assert u1 is not None
    assert u1["email"] == "dvnsabhiram071@gmail.com"
    assert u1["role"] == ROLE_SURVEILLANCE_ANALYST
    assert u1["must_change_password"] is True

    # 2. Read-Only Viewer account
    s2, u2, _ = authenticate_user("abhichowdary071@gmail.com", "Abhi@071", selected_role="viewer")
    assert s2 is True
    assert u2 is not None
    assert u2["email"] == "abhichowdary071@gmail.com"
    assert u2["role"] == ROLE_READ_ONLY_VIEWER
    assert u2["must_change_password"] is True

    # 3. System Administrator account
    s3, u3, _ = authenticate_user("duggineniabhiram170@gmail.com", "Abhi@071", selected_role="admin")
    assert s3 is True
    assert u3 is not None
    assert u3["email"] == "duggineniabhiram170@gmail.com"
    assert u3["role"] == ROLE_SYSTEM_ADMIN
    assert u3["must_change_password"] is True


def test_selected_role_validation_and_mismatch_rejection():
    # Attempting to log into Surveillance Analyst while selecting System Administrator
    success_bad, user_bad, msg_bad = authenticate_user(
        "dvnsabhiram071@gmail.com", "Abhi@071", selected_role="admin"
    )
    assert success_bad is False
    assert user_bad is None
    assert "Selected role does not match this account" in msg_bad

    # Attempting to log into Read-Only Viewer while selecting Surveillance Analyst
    s_v_bad, _, msg_v_bad = authenticate_user(
        "abhichowdary071@gmail.com", "Abhi@071", selected_role="analyst"
    )
    assert s_v_bad is False
    assert "Selected role does not match this account" in msg_v_bad

    # Attempting to log into System Administrator while selecting Read-Only Viewer
    s_a_bad, _, msg_a_bad = authenticate_user(
        "duggineniabhiram170@gmail.com", "Abhi@071", selected_role="viewer"
    )
    assert s_a_bad is False
    assert "Selected role does not match this account" in msg_a_bad


def test_invalid_credentials_rejected():
    success, user, msg = authenticate_user("dvnsabhiram071@gmail.com", "WrongPassword!")
    assert success is False
    assert user is None
    assert "Invalid email address or password" in msg

    success2, user2, msg2 = authenticate_user("nonexistent@domain.com", "AnyPass")
    assert success2 is False
    assert user2 is None


def test_mandatory_password_change_flow():
    email = "dvnsabhiram071@gmail.com"
    temp_pwd = "Abhi@071"

    # 1. First login verifies temporary password
    success, user, _ = authenticate_user(email, temp_pwd, selected_role="analyst")
    assert success is True
    assert user["must_change_password"] is True

    # 2. Rejection on mismatched confirmation
    ok, err = change_user_password(email, temp_pwd, "ValidPassword@123", "MismatchPassword@123")
    assert ok is False
    assert "confirmation do not match" in err

    # 3. Rejection on identical to temporary password
    ok, err = change_user_password(email, temp_pwd, temp_pwd, temp_pwd)
    assert ok is False
    assert "identical to the temporary password" in err

    # 4. Rejection on failing policy (<12 chars)
    ok, err = change_user_password(email, temp_pwd, "Short@1", "Short@1")
    assert ok is False
    assert "at least 12 characters" in err

    # 5. Successful password change satisfying policy
    new_pwd = "PermanentAnalystPass#2026"
    ok, msg = change_user_password(email, temp_pwd, new_pwd, new_pwd)
    assert ok is True
    assert "successfully updated" in msg

    # 6. Verify old password no longer works
    s_old, _, _ = authenticate_user(email, temp_pwd, selected_role="analyst")
    assert s_old is False

    # 7. Verify new password works and must_change_password is now False
    s_new, updated_user, _ = authenticate_user(email, new_pwd, selected_role="analyst")
    assert s_new is True
    assert updated_user["must_change_password"] is False


def test_role_based_permissions():
    # Read-Only Viewer permissions
    assert has_permission(ROLE_READ_ONLY_VIEWER, "can_view_dashboards") is True
    assert has_permission(ROLE_READ_ONLY_VIEWER, "can_view_trends") is True
    assert has_permission(ROLE_READ_ONLY_VIEWER, "can_view_alerts") is True
    assert has_permission(ROLE_READ_ONLY_VIEWER, "can_upload_ast_data") is False
    assert has_permission(ROLE_READ_ONLY_VIEWER, "can_modify_data") is False
    assert has_permission(ROLE_READ_ONLY_VIEWER, "can_manage_users") is False
    assert has_permission(ROLE_READ_ONLY_VIEWER, "can_configure_settings") is False

    # Surveillance Analyst permissions
    assert has_permission(ROLE_SURVEILLANCE_ANALYST, "can_view_dashboards") is True
    assert has_permission(ROLE_SURVEILLANCE_ANALYST, "can_upload_ast_data") is True
    assert has_permission(ROLE_SURVEILLANCE_ANALYST, "can_run_scenarios") is True
    assert has_permission(ROLE_SURVEILLANCE_ANALYST, "can_use_copilot") is True
    assert has_permission(ROLE_SURVEILLANCE_ANALYST, "can_manage_users") is False

    # System Administrator permissions
    assert has_permission(ROLE_SYSTEM_ADMIN, "can_view_dashboards") is True
    assert has_permission(ROLE_SYSTEM_ADMIN, "can_upload_ast_data") is True
    assert has_permission(ROLE_SYSTEM_ADMIN, "can_manage_users") is True
    assert has_permission(ROLE_SYSTEM_ADMIN, "can_configure_settings") is True
    assert has_permission(ROLE_SYSTEM_ADMIN, "can_view_audit_logs") is True


def test_audit_logging():
    logs = get_audit_logs()
    assert isinstance(logs, list)
    # Secrets or hashes must never appear in log details
    for entry in logs:
        assert "password_hash" not in json.dumps(entry)
        assert "Abhi@071" not in json.dumps(entry)
