"""
AMR Sentinel - Web Server & Routing Integration Tests (tests/test_server.py)
Verifies clean routing for root '/', '/landing.html', '/login.html', protected '/index.html',
backend PBKDF2 authentication, mandatory first-login password change, and session logout.
"""
import os
import sys
import json
import time
import socket
import threading
import urllib.request
import urllib.error
import http.client
from http.cookies import SimpleCookie
import pytest

# Ensure root directory is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import server
from src.auth import initialize_default_users, load_users


def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def run_test_server():
    """Spins up an instance of AMRSentinelHandler on an ephemeral port for testing."""
    initialize_default_users()
    test_port = get_free_port()
    httpd = server.http.server.ThreadingHTTPServer(('127.0.0.1', test_port), server.AMRSentinelHandler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    base_url = f"http://127.0.0.1:{test_port}"
    yield base_url
    httpd.shutdown()
    initialize_default_users(reset_passwords=True)


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Prevent auto-following 302 redirects so we can assert on them
        return None


def make_request(base_url, path, method="GET", data=None, cookies=None, follow_redirects=True):
    opener = urllib.request.build_opener() if follow_redirects else urllib.request.build_opener(NoRedirectHandler)
    url = f"{base_url}{path}"
    headers = {}
    body = None

    if cookies:
        headers["Cookie"] = cookies

    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with opener.open(req) as resp:
            content = resp.read().decode("utf-8")
            cookie_header = resp.headers.get("Set-Cookie")
            return resp.status, content, resp.headers, cookie_header
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        return e.code, content, e.headers, e.headers.get("Set-Cookie")


def test_root_url_serves_landing_page(run_test_server):
    """Opening the main website URL '/' must display the landing page matching reference design 1."""
    base_url = run_test_server
    status, content, headers, _ = make_request(base_url, "/")
    assert status == 200
    assert "AMR Sentinel" in content
    assert "Antimicrobial" in content
    assert "Intelligence" in content
    assert "in Real Time" in content
    assert "Explore Surveillance" in content
    assert "/login.html" in content


def test_landing_html_route(run_test_server):
    """Opening '/landing.html' must also serve the landing page with valid Sign In links."""
    base_url = run_test_server
    status, content, headers, _ = make_request(base_url, "/landing.html")
    assert status == 200
    assert "Smarter Surveillance. Healthier Tomorrows." in content
    assert "/login.html" in content


def test_login_html_route_and_role_selector(run_test_server):
    """Opening '/login.html' displays role selector with 3 options and contains no embedded user databases."""
    base_url = run_test_server
    status, content, headers, _ = make_request(base_url, "/login.html")
    assert status == 200
    assert "Select Your Role" in content
    assert "Surveillance Analyst" in content
    assert "Read-Only Viewer" in content
    assert "System Administrator" in content
    assert 'href="/"' in content  # Back to Home link navigates to '/'
    assert "USER_DATABASE" not in content  # Must NOT contain client-side credentials
    assert "value=\"Abhi@071\"" in content  # UI form placeholder/preview only


def test_unauthorized_dashboard_access_redirects_to_login(run_test_server):
    """Direct access to '/index.html' or '/dashboard' without a session must redirect (302) to '/login.html'."""
    base_url = run_test_server
    status, content, headers, _ = make_request(base_url, "/index.html", follow_redirects=False)
    assert status == 302
    assert headers.get("Location") == "/login.html"

    status2, _, headers2, _ = make_request(base_url, "/dashboard", follow_redirects=False)
    assert status2 == 302
    assert headers2.get("Location") == "/login.html"


def test_role_mismatch_rejected(run_test_server):
    """Selecting a role that does not match the server-stored account role is rejected with HTTP 401."""
    base_url = run_test_server
    initialize_default_users(reset_passwords=True)
    status, content, _, _ = make_request(base_url, "/api/login", method="POST", data={
        "email": "dvnsabhiram071@gmail.com",
        "password": "Abhi@071",
        "selected_role": "admin"  # Mismatch: dvnsabhiram071@gmail.com is analyst
    })
    assert status == 401
    res = json.loads(content)
    assert res["success"] is False
    assert "Selected role does not match this account" in res["message"]


def test_invalid_login_rejected(run_test_server):
    """API login with invalid credentials returns HTTP 401."""
    base_url = run_test_server
    status, content, _, _ = make_request(base_url, "/api/login", method="POST", data={
        "email": "dvnsabhiram071@gmail.com",
        "password": "WrongPassword999!",
        "selected_role": "analyst"
    })
    assert status == 401
    res = json.loads(content)
    assert res["success"] is False
    assert "Invalid email address or password" in res["message"]


def test_first_login_flow_and_mandatory_password_change(run_test_server):
    """
    Login with temporary credentials flags must_change_password=True,
    prevents dashboard entry until permanent password policy is satisfied,
    then permits access upon change.
    """
    base_url = run_test_server
    initialize_default_users()

    # 1. Login with temporary password as System Administrator
    status, content, _, cookie_header = make_request(base_url, "/api/login", method="POST", data={
        "email": "duggineniabhiram170@gmail.com",
        "password": "Abhi@071",
        "selected_role": "admin"
    })
    assert status == 200
    res = json.loads(content)
    assert res["success"] is True
    assert res["must_change_password"] is True
    assert cookie_header is not None
    assert "amr_session=" in cookie_header

    # Extract session cookie
    cookie = SimpleCookie()
    cookie.load(cookie_header)
    session_val = cookie["amr_session"].value
    cookie_str = f"amr_session={session_val}"

    # 2. Accessing dashboard while must_change_password=True must redirect to password change
    dash_status, _, dash_headers, _ = make_request(
        base_url, "/index.html", cookies=cookie_str, follow_redirects=False
    )
    assert dash_status == 302
    assert "/login.html?change_password=1" in dash_headers.get("Location")

    # 3. Attempting to change password to a non-compliant one (too short)
    pwd_status_bad, pwd_content_bad, _, _ = make_request(
        base_url, "/api/change-password", method="POST", cookies=cookie_str, data={
            "email": "duggineniabhiram170@gmail.com",
            "current_password": "Abhi@071",
            "new_password": "Short1!",
            "confirm_password": "Short1!"
        }
    )
    assert pwd_status_bad == 400
    assert "at least 12 characters" in pwd_content_bad

    # 4. Attempting to reuse the temporary password
    pwd_status_same, pwd_content_same, _, _ = make_request(
        base_url, "/api/change-password", method="POST", cookies=cookie_str, data={
            "email": "duggineniabhiram170@gmail.com",
            "current_password": "Abhi@071",
            "new_password": "Abhi@071",
            "confirm_password": "Abhi@071"
        }
    )
    assert pwd_status_same == 400
    assert "identical to the temporary password" in pwd_content_same

    # 5. Set compliant permanent password
    permanent_pwd = "PermanentAdmin#2026!Secure"
    pwd_status_ok, pwd_content_ok, _, _ = make_request(
        base_url, "/api/change-password", method="POST", cookies=cookie_str, data={
            "email": "duggineniabhiram170@gmail.com",
            "current_password": "Abhi@071",
            "new_password": permanent_pwd,
            "confirm_password": permanent_pwd
        }
    )
    assert pwd_status_ok == 200
    assert json.loads(pwd_content_ok)["success"] is True

    # 6. Now accessing dashboard with session cookie must return 200 and serve dashboard!
    dash_status_ok, dash_content_ok, _, _ = make_request(
        base_url, "/index.html", cookies=cookie_str, follow_redirects=False
    )
    assert dash_status_ok == 200
    assert "AMR Sentinel" in dash_content_ok

    # 7. Check /api/session endpoint
    sess_status, sess_content, _, _ = make_request(base_url, "/api/session", cookies=cookie_str)
    assert sess_status == 200
    sess_data = json.loads(sess_content)
    assert sess_data["authenticated"] is True
    assert sess_data["user"]["role"] == "admin"
    assert sess_data["permissions"]["can_manage_users"] is True

    # 8. Check /api/users endpoint (Admin authorized)
    users_status, users_content, _, _ = make_request(base_url, "/api/users", cookies=cookie_str)
    assert users_status == 200
    users_data = json.loads(users_content)
    assert users_data["success"] is True
    assert len(users_data["users"]) >= 3

    # 9. Test logout endpoint
    logout_status, logout_content, _, logout_cookie = make_request(
        base_url, "/api/logout", method="POST", cookies=cookie_str
    )
    assert logout_status == 200
    assert json.loads(logout_content)["success"] is True

    # Subsequent access without session redirects to login again
    final_status, _, final_headers, _ = make_request(
        base_url, "/index.html", cookies="amr_session=invalid", follow_redirects=False
    )
    assert final_status == 302
    assert final_headers.get("Location") == "/login.html"


def test_viewer_role_restrictions(run_test_server):
    """Read-Only Viewer is forbidden from uploading AST data and viewing admin users."""
    base_url = run_test_server
    initialize_default_users()

    # 1. Login as Read-Only Viewer
    status, content, _, cookie_header = make_request(base_url, "/api/login", method="POST", data={
        "email": "abhichowdary071@gmail.com",
        "password": "Abhi@071",
        "selected_role": "viewer"
    })
    assert status == 200
    cookie = SimpleCookie()
    cookie.load(cookie_header)
    cookie_str = f"amr_session={cookie['amr_session'].value}"

    # Change password to satisfy mandatory password change
    make_request(
        base_url, "/api/change-password", method="POST", cookies=cookie_str, data={
            "email": "abhichowdary071@gmail.com",
            "current_password": "Abhi@071",
            "new_password": "PermanentViewer#2026!Secure",
            "confirm_password": "PermanentViewer#2026!Secure"
        }
    )

    # 2. Attempt /api/upload as Viewer -> 403 Forbidden
    upload_status, upload_content, _, _ = make_request(
        base_url, "/api/upload", method="POST", cookies=cookie_str, data={"data": "test"}
    )
    assert upload_status == 403
    assert "Permission denied" in upload_content

    # 3. Attempt /api/users as Viewer -> 403 Forbidden
    users_status, users_content, _, _ = make_request(
        base_url, "/api/users", method="GET", cookies=cookie_str
    )
    assert users_status == 403
    assert "Access denied" in users_content


def test_demo_login_and_surveillance_analyst_role(run_test_server):
    """Demo login grants Surveillance Analyst role and allows direct dashboard access."""
    base_url = run_test_server
    status, content, _, cookie_header = make_request(base_url, "/api/demo-login", method="POST")
    assert status == 200
    res = json.loads(content)
    assert res["success"] is True
    assert res["user"]["role"] == "analyst"
    assert res["must_change_password"] is False

    cookie = SimpleCookie()
    cookie.load(cookie_header)
    cookie_str = f"amr_session={cookie['amr_session'].value}"

    dash_status, dash_content, _, _ = make_request(base_url, "/index.html", cookies=cookie_str, follow_redirects=False)
    assert dash_status == 200


def test_analyst_allowed_csv_upload_and_validation(run_test_server):
    """Surveillance Analyst is authorized to upload AST laboratory data and receive validation metrics."""
    base_url = run_test_server
    initialize_default_users(reset_passwords=True)

    # 1. Login as Surveillance Analyst
    status, _, _, cookie_header = make_request(base_url, "/api/login", method="POST", data={
        "email": "dvnsabhiram071@gmail.com",
        "password": "Abhi@071",
        "selected_role": "analyst"
    })
    assert status == 200
    cookie = SimpleCookie()
    cookie.load(cookie_header)
    cookie_str = f"amr_session={cookie['amr_session'].value}"

    # Satisfy mandatory password change
    make_request(
        base_url, "/api/change-password", method="POST", cookies=cookie_str, data={
            "email": "dvnsabhiram071@gmail.com",
            "current_password": "Abhi@071",
            "new_password": "PermanentAnalyst#2026!Secure",
            "confirm_password": "PermanentAnalyst#2026!Secure"
        }
    )

    # 2. Upload valid CSV content
    sample_csv = (
        "record_id,test_date,organism,antibiotic,department,specimen_type,result_category\n"
        "REC-001,2024-11-01,E. coli,Ciprofloxacin,ICU,Blood,Resistant\n"
        "REC-002,2024-11-02,K. pneumoniae,Meropenem,Ward,Urine,Susceptible\n"
    )
    up_status, up_content, _, _ = make_request(base_url, "/api/upload", method="POST", cookies=cookie_str, data={
        "csv_content": sample_csv,
        "filename": "lab_ast_batch_01.csv"
    })
    assert up_status == 200
    res = json.loads(up_content)
    assert res["success"] is True
    assert res["valid_rows"] == 2
    assert res["excluded_rows"] == 0


def test_viewer_denied_alert_acknowledgment_and_analyst_allowed(run_test_server):
    """Read-Only Viewer is forbidden from acknowledging alerts (403), while Analyst is authorized (200)."""
    base_url = run_test_server
    initialize_default_users(reset_passwords=True)

    # 1. Viewer login
    _, _, _, v_cookie_header = make_request(base_url, "/api/login", method="POST", data={
        "email": "abhichowdary071@gmail.com",
        "password": "Abhi@071",
        "selected_role": "viewer"
    })
    cookie = SimpleCookie()
    cookie.load(v_cookie_header)
    v_cookie = f"amr_session={cookie['amr_session'].value}"

    make_request(
        base_url, "/api/change-password", method="POST", cookies=v_cookie, data={
            "email": "abhichowdary071@gmail.com",
            "current_password": "Abhi@071",
            "new_password": "PermanentViewer#2026!Secure",
            "confirm_password": "PermanentViewer#2026!Secure"
        }
    )

    # Viewer attempt to acknowledge alert -> 403 Forbidden
    v_ack_status, v_ack_content, _, _ = make_request(
        base_url, "/api/alerts/acknowledge", method="POST", cookies=v_cookie, data={"alert_id": "ALT-001"}
    )
    assert v_ack_status == 403
    assert "Permission denied" in v_ack_content

    # 2. Analyst login
    _, _, _, a_cookie_header = make_request(base_url, "/api/login", method="POST", data={
        "email": "dvnsabhiram071@gmail.com",
        "password": "Abhi@071",
        "selected_role": "analyst"
    })
    cookie = SimpleCookie()
    cookie.load(a_cookie_header)
    a_cookie = f"amr_session={cookie['amr_session'].value}"

    make_request(
        base_url, "/api/change-password", method="POST", cookies=a_cookie, data={
            "email": "dvnsabhiram071@gmail.com",
            "current_password": "Abhi@071",
            "new_password": "PermanentAnalyst#2026!Secure",
            "confirm_password": "PermanentAnalyst#2026!Secure"
        }
    )

    # Analyst attempt to acknowledge alert -> 200 OK
    a_ack_status, a_ack_content, _, _ = make_request(
        base_url, "/api/alerts/acknowledge", method="POST", cookies=a_cookie, data={"alert_id": "ALT-001"}
    )
    assert a_ack_status == 200
    a_res = json.loads(a_ack_content)
    assert a_res["success"] is True
    assert a_res["status"] == "Acknowledged"


def test_admin_management_and_toggle_surveillance(run_test_server):
    """System Administrator can manage users, view audit logs, and toggle surveillance view."""
    base_url = run_test_server
    initialize_default_users(reset_passwords=True)

    # 1. Admin login
    status, _, _, cookie_header = make_request(base_url, "/api/login", method="POST", data={
        "email": "duggineniabhiram170@gmail.com",
        "password": "Abhi@071",
        "selected_role": "admin"
    })
    assert status == 200
    cookie = SimpleCookie()
    cookie.load(cookie_header)
    admin_cookie = f"amr_session={cookie['amr_session'].value}"

    make_request(
        base_url, "/api/change-password", method="POST", cookies=admin_cookie, data={
            "email": "duggineniabhiram170@gmail.com",
            "current_password": "Abhi@071",
            "new_password": "PermanentAdmin#2026!Secure",
            "confirm_password": "PermanentAdmin#2026!Secure"
        }
    )

    # 2. Access /api/users -> 200 OK
    u_status, u_content, _, _ = make_request(base_url, "/api/users", method="GET", cookies=admin_cookie)
    assert u_status == 200
    u_data = json.loads(u_content)
    assert u_data["success"] is True
    assert len(u_data["users"]) >= 3

    # 3. Access /api/audit-log -> 200 OK
    log_status, log_content, _, _ = make_request(base_url, "/api/audit-log", method="GET", cookies=admin_cookie)
    assert log_status == 200
    log_data = json.loads(log_content)
    assert log_data["success"] is True

    # 4. Toggle surveillance view -> 200 OK
    t_status, t_content, _, _ = make_request(
        base_url, "/api/admin/toggle-surveillance", method="POST", cookies=admin_cookie, data={"mode": "operational"}
    )
    assert t_status == 200
    assert json.loads(t_content)["mode"] == "operational"


def test_admin_provision_and_reset_temporary_password(run_test_server):
    """System Administrator can provision new accounts with temporary credentials and reset passwords."""
    base_url = run_test_server
    initialize_default_users(reset_passwords=True)

    # 1. Login as Admin
    status, _, _, cookie_header = make_request(base_url, "/api/login", method="POST", data={
        "email": "duggineniabhiram170@gmail.com",
        "password": "Abhi@071",
        "selected_role": "admin"
    })
    assert status == 200
    cookie = SimpleCookie()
    cookie.load(cookie_header)
    admin_cookie = f"amr_session={cookie['amr_session'].value}"

    # Satisfy password change
    make_request(
        base_url, "/api/change-password", method="POST", cookies=admin_cookie, data={
            "email": "duggineniabhiram170@gmail.com",
            "current_password": "Abhi@071",
            "new_password": "PermanentAdmin#2026!Secure",
            "confirm_password": "PermanentAdmin#2026!Secure"
        }
    )

    # 2. Provision new user as Admin -> 201 Created
    prov_status, prov_content, _, _ = make_request(
        base_url, "/api/users/provision", method="POST", cookies=admin_cookie, data={
            "name": "Dr. Sarah Rao",
            "email": "sarah.rao@amr-network.org",
            "role": "analyst",
            "temporary_password": "Temp@Password2026!"
        }
    )
    assert prov_status == 201
    prov_data = json.loads(prov_content)
    assert prov_data["success"] is True
    assert prov_data["user"]["email"] == "sarah.rao@amr-network.org"
    assert prov_data["user"]["must_change_password"] is True

    # Duplicate provisioning -> 409 Conflict
    dup_status, _, _, _ = make_request(
        base_url, "/api/users/provision", method="POST", cookies=admin_cookie, data={
            "name": "Duplicate User",
            "email": "sarah.rao@amr-network.org",
            "role": "analyst"
        }
    )
    assert dup_status == 409

    # 3. Reset temporary password for provisioned user -> 200 OK
    reset_status, reset_content, _, _ = make_request(
        base_url, "/api/users/reset-temp-password", method="POST", cookies=admin_cookie, data={
            "email": "sarah.rao@amr-network.org",
            "temporary_password": "NewReset@Pass2026!"
        }
    )
    assert reset_status == 200
    assert json.loads(reset_content)["success"] is True

    # 4. Non-admin attempting provisioning -> 403 Forbidden
    demo_status, _, _, demo_cookie_header = make_request(base_url, "/api/demo-login", method="POST")
    demo_cookie_val = SimpleCookie()
    demo_cookie_val.load(demo_cookie_header)
    analyst_cookie = f"amr_session={demo_cookie_val['amr_session'].value}"

    denied_status, _, _, _ = make_request(
        base_url, "/api/users/provision", method="POST", cookies=analyst_cookie, data={
            "email": "unauthorized@test.com", "role": "analyst"
        }
    )
    assert denied_status == 403


def test_admin_policy_simulator_and_auth_runner(run_test_server):
    """Admin can simulate RBAC policy decisions and trigger live security suite assertions."""
    base_url = run_test_server
    initialize_default_users(reset_passwords=True)

    # 1. Login as Admin
    status, _, _, cookie_header = make_request(base_url, "/api/login", method="POST", data={
        "email": "duggineniabhiram170@gmail.com",
        "password": "Abhi@071",
        "selected_role": "admin"
    })
    cookie = SimpleCookie()
    cookie.load(cookie_header)
    admin_cookie = f"amr_session={cookie['amr_session'].value}"

    make_request(
        base_url, "/api/change-password", method="POST", cookies=admin_cookie, data={
            "email": "duggineniabhiram170@gmail.com",
            "current_password": "Abhi@071",
            "new_password": "PermanentAdmin#2026!Secure",
            "confirm_password": "PermanentAdmin#2026!Secure"
        }
    )

    # 2. Simulate policy: Viewer attempting upload -> DENIED
    sim1_status, sim1_content, _, _ = make_request(
        base_url, "/api/admin/policy-simulate", method="POST", cookies=admin_cookie, data={
            "role": "viewer",
            "action": "upload_ast"
        }
    )
    assert sim1_status == 200
    sim1_data = json.loads(sim1_content)
    assert sim1_data["decision"] == "DENIED"
    assert sim1_data["allowed"] is False

    # 3. Simulate policy: Analyst attempting upload -> ALLOWED
    sim2_status, sim2_content, _, _ = make_request(
        base_url, "/api/admin/policy-simulate", method="POST", cookies=admin_cookie, data={
            "role": "analyst",
            "action": "upload_ast"
        }
    )
    assert sim2_status == 200
    sim2_data = json.loads(sim2_content)
    assert sim2_data["decision"] == "ALLOWED"
    assert sim2_data["allowed"] is True

    # 4. Run live authorization tests -> 200 OK (5/5 PASS)
    run_status, run_content, _, _ = make_request(
        base_url, "/api/admin/run-auth-tests", method="POST", cookies=admin_cookie
    )
    assert run_status == 200
    run_data = json.loads(run_content)
    assert run_data["success"] is True
    assert run_data["passed"] == 5
    assert len(run_data["results"]) == 5

    # 5. Get compliance report -> 200 OK
    comp_status, comp_content, _, _ = make_request(
        base_url, "/api/admin/compliance-report", method="GET", cookies=admin_cookie
    )
    assert comp_status == 200
    comp_data = json.loads(comp_content)
    assert comp_data["success"] is True
    assert len(comp_data["compliance_frameworks"]) >= 3
    assert comp_data["user_registry_summary"]["total_accounts"] >= 3



def test_index_html_contains_all_three_role_workspaces_and_access_denied():
    """Verify that index.html contains all required sections for Analyst, Viewer, and Admin workspaces."""
    index_path = os.path.join(PROJECT_ROOT, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Analyst Sections
    assert 'id="view-overview"' in html
    assert 'id="view-map"' in html
    assert 'id="view-trends"' in html
    assert 'id="view-alerts"' in html
    assert 'id="view-scenario"' in html
    assert 'id="view-copilot"' in html
    assert 'id="view-upload"' in html
    assert 'id="view-quality"' in html
    assert 'id="view-reports"' in html

    # Access Denied Guard View
    assert 'id="view-access-denied"' in html

    # System Administrator Dedicated Workspace Sections (Phase 1, 2, and 3)
    assert 'id="view-admin-overview"' in html
    assert 'id="view-admin-users"' in html
    assert 'id="view-admin-roles"' in html
    assert 'id="view-admin-policy-sim"' in html
    assert 'id="view-admin-auth-tests"' in html
    assert 'id="view-admin-sources"' in html
    assert 'id="view-admin-compliance"' in html
    assert 'id="view-admin-audit"' in html
    assert 'id="view-admin-health"' in html
    assert 'id="view-admin-advanced"' in html

    # Confirm old "Administrative Isolation Policy" notice banner is completely removed
    assert "Administrative Isolation Policy" not in html

    # Admin Workspace toggle button
    assert 'admin-toggle-mode-btn' in html
    assert 'toggleAdminOperationalMode' in html


