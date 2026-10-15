"""
AMR Sentinel - Role-Based Authentication & User Authorization Engine (src/auth.py)
Provides salted password hashing, password policy validation, initial account bootstrap,
three-role permission enforcement, first-login mandatory password change, and audit logging.
"""
import os
import json
import re
import hashlib
import secrets
import time
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, List, Optional

USERS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "users.json")
AUDIT_LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "audit_log.json")

# Role definitions & enforced server-side permission matrix
ROLE_SYSTEM_ADMIN = "admin"
ROLE_SURVEILLANCE_ANALYST = "analyst"
ROLE_READ_ONLY_VIEWER = "viewer"

ROLE_NAMES = {
    ROLE_SYSTEM_ADMIN: "System Administrator",
    ROLE_SURVEILLANCE_ANALYST: "Surveillance Analyst",
    ROLE_READ_ONLY_VIEWER: "Read-Only Viewer",
}

PERMISSIONS: Dict[str, Dict[str, bool]] = {
    ROLE_READ_ONLY_VIEWER: {
        "can_view_dashboards": True,
        "can_view_trends": True,
        "can_view_maps": True,
        "can_view_alerts": True,
        "can_view_reports": True,
        "can_acknowledge_alerts": False,
        "can_upload_ast_data": False,
        "can_modify_data": False,
        "can_run_scenarios": False,
        "can_use_copilot": False,
        "can_manage_users": False,
        "can_configure_settings": False,
        "can_view_audit_logs": False,
    },
    ROLE_SURVEILLANCE_ANALYST: {
        "can_view_dashboards": True,
        "can_view_trends": True,
        "can_view_maps": True,
        "can_view_alerts": True,
        "can_view_reports": True,
        "can_acknowledge_alerts": True,
        "can_upload_ast_data": True,
        "can_modify_data": True,
        "can_run_scenarios": True,
        "can_use_copilot": True,
        "can_manage_users": False,
        "can_configure_settings": False,
        "can_view_audit_logs": False,
    },
    ROLE_SYSTEM_ADMIN: {
        "can_view_dashboards": True,
        "can_view_trends": True,
        "can_view_maps": True,
        "can_view_alerts": True,
        "can_view_reports": True,
        "can_acknowledge_alerts": True,
        "can_upload_ast_data": True,
        "can_modify_data": True,
        "can_run_scenarios": True,
        "can_use_copilot": True,
        "can_manage_users": True,
        "can_configure_settings": True,
        "can_view_audit_logs": True,
    },
}


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    Hashes a password with PBKDF2-HMAC-SHA256 and 100,000 rounds using a cryptographically secure salt.
    Returns (hex_hash, hex_salt).
    """
    if salt is None:
        salt_bytes = secrets.token_bytes(16)
        salt = salt_bytes.hex()
    else:
        salt_bytes = bytes.fromhex(salt)

    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 100000)
    return dk.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verifies a password against a stored PBKDF2 hash using constant-time comparison."""
    computed_hash, _ = hash_password(password, salt=salt)
    return secrets.compare_digest(computed_hash, password_hash)


def validate_password_policy(password: str) -> Tuple[bool, List[str]]:
    """
    Enforces password complexity requirements for newly chosen passwords:
    - Minimum 12 characters.
    - At least one uppercase letter (A-Z).
    - At least one lowercase letter (a-z).
    - At least one digit (0-9).
    - At least one special symbol.
    Returns (is_valid, list_of_error_messages).
    """
    errors = []
    if len(password) < 12:
        errors.append("Password must be at least 12 characters long.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter (A-Z).")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter (a-z).")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one number (0-9).")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_=+[\]\\/`~]", password):
        errors.append("Password must contain at least one special character (!@#$%^&*...).")

    return (len(errors) == 0, errors)


BOOTSTRAP_ACCOUNTS = [
    {
        "email": "dvnsabhiram071@gmail.com",
        "name": "Abhiram DVN",
        "role": ROLE_SURVEILLANCE_ANALYST,
    },
    {
        "email": "abhichowdary071@gmail.com",
        "name": "Abhi Chowdary",
        "role": ROLE_READ_ONLY_VIEWER,
    },
    {
        "email": "duggineniabhiram170@gmail.com",
        "name": "Duggineni Abhiram",
        "role": ROLE_SYSTEM_ADMIN,
    },
]

DEFAULT_INITIAL_PASSWORD = os.environ.get("INITIAL_DEFAULT_PASSWORD", "Abhi@071")


def normalize_role(role: Optional[str]) -> Optional[str]:
    """Normalizes role strings across slug and display variants."""
    if not role:
        return None
    r = role.strip().lower()
    if "admin" in r:
        return ROLE_SYSTEM_ADMIN
    if "analyst" in r or "surveillance" in r:
        return ROLE_SURVEILLANCE_ANALYST
    if "view" in r or "read" in r or "observer" in r:
        return ROLE_READ_ONLY_VIEWER
    return r


def load_users() -> Dict[str, Dict[str, Any]]:
    """Loads user dictionary from storage, ensuring default accounts exist (idempotent)."""
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
            # Ensure the 3 required bootstrap accounts exist with designated roles
            missing = any(acc["email"] not in users for acc in BOOTSTRAP_ACCOUNTS)
            role_mismatch = (
                users.get("dvnsabhiram071@gmail.com", {}).get("role") != ROLE_SURVEILLANCE_ANALYST
                or users.get("abhichowdary071@gmail.com", {}).get("role") != ROLE_READ_ONLY_VIEWER
                or users.get("duggineniabhiram170@gmail.com", {}).get("role") != ROLE_SYSTEM_ADMIN
            )
            if not missing and not role_mismatch:
                return users
        except Exception:
            pass

    return initialize_default_users()


def save_users(users: Dict[str, Dict[str, Any]]) -> None:
    """Saves the user dictionary safely to disk with retry for Windows/OneDrive file locks."""
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    temp_file = USERS_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

    for attempt in range(5):
        try:
            os.replace(temp_file, USERS_FILE)
            return
        except (PermissionError, OSError):
            time.sleep(0.05 * (attempt + 1))

    # Fallback in case of persistent file lock
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
    except Exception:
        pass


def initialize_default_users(reset_passwords: bool = False) -> Dict[str, Dict[str, Any]]:
    """
    Idempotent account bootstrap: Initializes the three required accounts
    with initial temporary credentials and mandatory first-login password change:
    1. Surveillance Analyst: dvnsabhiram071@gmail.com
    2. Read-Only Viewer:     abhichowdary071@gmail.com
    3. System Administrator:  duggineniabhiram170@gmail.com
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    existing_users: Dict[str, Dict[str, Any]] = {}

    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                existing_users = json.load(f)
        except Exception:
            existing_users = {}

    if reset_passwords:
        users = {}
    else:
        users = dict(existing_users)

    temp_pwd = os.environ.get("INITIAL_DEFAULT_PASSWORD", DEFAULT_INITIAL_PASSWORD)

    for item in BOOTSTRAP_ACCOUNTS:
        email = item["email"]
        role = item["role"]
        name = item["name"]

        if email in users and not reset_passwords:
            # Preserve existing user password hash and state, but ensure designated role
            users[email]["role"] = role
            users[email]["name"] = name
            if "must_change_password" not in users[email]:
                users[email]["must_change_password"] = True
        else:
            p_hash, p_salt = hash_password(temp_pwd)
            users[email] = {
                "email": email,
                "name": name,
                "password_hash": p_hash,
                "salt": p_salt,
                "role": role,
                "must_change_password": True,
                "created_at": now_iso,
                "last_login": None,
            }

    save_users(users)
    audit_log_event("SYSTEM_BOOTSTRAP", "system", "Initialized and synchronized 3-role bootstrap accounts")
    return users


def authenticate_user(
    email: str,
    password: str,
    selected_role: Optional[str] = None
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Validates user credentials against stored salted password hashes
    and verifies that the client-selected role matches the server-stored account role.
    Returns (success, safe_user_data, message).
    """
    email_clean = email.strip().lower()
    users = load_users()

    # Look up user case-insensitively
    user = None
    user_key = None
    for k, u in users.items():
        if k.lower() == email_clean or u.get("email", "").lower() == email_clean:
            user = u
            user_key = k
            break

    if not user:
        return False, None, "Invalid email address or password."

    if not verify_password(password, user["password_hash"], user["salt"]):
        audit_log_event("LOGIN_FAILED", email_clean, "Incorrect password attempt")
        return False, None, "Invalid email address or password."

    # Server-side validation: Ensure selected role matches server-stored role
    if selected_role:
        norm_selected = normalize_role(selected_role)
        if norm_selected != user.get("role"):
            account_role_label = ROLE_NAMES.get(user.get("role", ""), user.get("role", ""))
            audit_log_event(
                "LOGIN_ROLE_MISMATCH",
                email_clean,
                f"Selected role '{selected_role}' rejected. Account is '{user.get('role')}'"
            )
            return False, None, f"Selected role does not match this account. This account is registered as {account_role_label}."

    # Update last login
    now_iso = datetime.now(timezone.utc).isoformat()
    users[user_key]["last_login"] = now_iso
    save_users(users)

    safe_user_copy = {k: v for k, v in user.items() if k not in ("password_hash", "salt")}
    safe_user_copy["last_login"] = now_iso

    audit_log_event("LOGIN_SUCCESS", email_clean, f"Successful authentication as {user.get('role')}")
    return True, safe_user_copy, "Authentication successful."


def get_all_users_safe() -> List[Dict[str, Any]]:
    """Returns sanitized list of registered user accounts for administrative display."""
    users = load_users()
    safe_list = []
    for email, u in users.items():
        safe_list.append({
            "email": u.get("email", email),
            "name": u.get("name", ""),
            "role": u.get("role", ROLE_READ_ONLY_VIEWER),
            "role_name": ROLE_NAMES.get(u.get("role", ""), u.get("role", "")),
            "must_change_password": bool(u.get("must_change_password", False)),
            "created_at": u.get("created_at"),
            "last_login": u.get("last_login"),
        })
    return safe_list


def change_user_password(
    email: str,
    current_password: str,
    new_password: str,
    confirm_password: str
) -> Tuple[bool, str]:
    """
    Validates current credentials, enforces the password policy on the new password,
    checks confirmation match, and updates the stored hash and must_change_password status.
    """
    email_clean = email.strip().lower()
    users = load_users()

    user_key = None
    for k, u in users.items():
        if k.lower() == email_clean or u.get("email", "").lower() == email_clean:
            user_key = k
            break

    if not user_key:
        return False, "User account not found."

    user = users[user_key]

    if not verify_password(current_password, user["password_hash"], user["salt"]):
        return False, "Current password does not match."

    if new_password != confirm_password:
        return False, "New password and confirmation do not match."

    if new_password == current_password:
        return False, "New password cannot be identical to the temporary password."

    is_valid, policy_errors = validate_password_policy(new_password)
    if not is_valid:
        return False, " ".join(policy_errors)

    new_hash, new_salt = hash_password(new_password)
    users[user_key]["password_hash"] = new_hash
    users[user_key]["salt"] = new_salt
    users[user_key]["must_change_password"] = False
    users[user_key]["password_changed_at"] = datetime.now(timezone.utc).isoformat()
    save_users(users)

    audit_log_event("PASSWORD_CHANGED", email_clean, "User updated password and satisfied policy")
    return True, "Password successfully updated."


def has_permission(role: str, permission: str) -> bool:
    """Server-side check: Returns True if the specified role has the requested permission."""
    role_perms = PERMISSIONS.get(role, PERMISSIONS[ROLE_READ_ONLY_VIEWER])
    return role_perms.get(permission, False)


def audit_log_event(action: str, user_email: str, details: str) -> None:
    """Appends an event to the security audit log without logging sensitive data."""
    os.makedirs(os.path.dirname(AUDIT_LOG_FILE), exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "user": user_email,
        "details": details,
    }
    log_entries = []
    if os.path.exists(AUDIT_LOG_FILE):
        try:
            with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                log_entries = json.load(f)
        except Exception:
            log_entries = []

    log_entries.append(entry)
    # Retain the most recent 500 audit events
    if len(log_entries) > 500:
        log_entries = log_entries[-500:]

    try:
        with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log_entries, f, indent=2)
    except Exception:
        pass


def get_audit_logs() -> List[Dict[str, Any]]:
    """Retrieves recent audit log events."""
    if os.path.exists(AUDIT_LOG_FILE):
        try:
            with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []
