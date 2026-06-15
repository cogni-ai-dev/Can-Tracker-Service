from pathlib import Path

HTML_PATH = Path(__file__).resolve().parents[2] / "remixed-c3e65622.html"
HTML = HTML_PATH.read_text(encoding="utf-8")
SCRIPT = HTML.split("<script>", 1)[1].rsplit("</script>", 1)[0]


def test_frontend_bootstraps_through_authenticated_api_session() -> None:
    assert "api.get('/auth/me')" in SCRIPT
    assert "api.post('/auth/login'" in SCRIPT
    assert "ensureAuthenticated()" in SCRIPT
    assert "afterAuthenticated()" in SCRIPT
    assert "seedData" not in SCRIPT


def test_frontend_exposes_logout_action() -> None:
    assert 'id="logout-button"' in HTML
    assert "onclick=\"logout()\"" in HTML
    assert "api.request('POST', '/auth/logout')" in SCRIPT
    assert "resetSessionState()" in SCRIPT
    assert "showLogin()" in SCRIPT


def test_frontend_exposes_change_password_action() -> None:
    required_markup = [
        'id="change-password-button"',
        'onclick="openChangePassword()"',
        'id="password-modal"',
        'id="cp-current"',
        'id="cp-new"',
        'id="cp-confirm"',
    ]
    for snippet in required_markup:
        assert snippet in HTML
    assert "api.post('/auth/change-password'" in SCRIPT
    assert "New password and confirmation do not match." in SCRIPT


def test_major_read_screens_are_wired_to_backend_endpoints() -> None:
    required_snippets = [
        "api.get('/dashboard/summary'",
        "api.get('/tasks'",
        "api.get('/tasks/summary'",
        "api.get('/families'",
        "api.get(`/dashboard/families/${fid}`",
        "api.get('/members'",
    ]
    for snippet in required_snippets:
        assert snippet in SCRIPT


def test_family_and_member_writes_use_backend_mutations() -> None:
    required_snippets = [
        "api.post('/families'",
        "api.patch(`/families/${db.editFamilyId}`",
        "api.post(`/families/${db.currentFamilyId}/members`",
        "api.patch(`/members/${db.editMemberId}`",
        "api.delete(`/members/${mid}`",
    ]
    for snippet in required_snippets:
        assert snippet in SCRIPT


def test_reports_use_backend_preview_and_export_endpoints() -> None:
    assert "api.get(`/reports/${type}/preview`" in SCRIPT
    assert "api.download(`/reports/${type}/export`" in SCRIPT
    assert "function getReportData" not in SCRIPT
    assert "new Blob(['\\uFEFF'" not in SCRIPT


def test_status_and_task_tabs_use_backend_filters_not_local_calculations() -> None:
    required_filters = [
        "params.kyc_status = 'Validated'",
        "params.kyc_status = 'Registered'",
        "params.kyc_status = 'No KYC'",
        "params.payeezz_status = 'Not Available'",
        "params.payeezz_status = 'Sent for Approval'",
        "params.payeezz_status = 'Aggregator Accepted'",
        "params.mobile_status = 'Not Verified'",
        "params.email_status = 'Not Verified'",
        "params.nominee_status = 'Not Verified'",
        "params.type = tab",
    ]
    for snippet in required_filters:
        assert snippet in SCRIPT
    assert "function getTaskList" not in SCRIPT


def test_admin_user_management_page_uses_users_api() -> None:
    assert 'id="page-admin-users"' in HTML
    assert "Admin Portal" in HTML
    assert "navigate('admin-users')" in HTML
    required_snippets = [
        "api.get('/users'",
        "api.post('/users'",
        "api.patch(`/users/${db.editUserId}`",
        "api.delete(`/users/${userId}`",
        "api.patch(`/users/${userId}`, { is_active: true })",
        "await loadRMs()",
    ]
    for snippet in required_snippets:
        assert snippet in SCRIPT


def test_admin_user_modal_handles_create_edit_password_rules() -> None:
    required_markup = [
        'id="user-modal"',
        'id="u-name"',
        'id="u-email"',
        'id="u-role"',
        'id="u-active"',
        'id="u-password"',
        'id="u-password-help"',
    ]
    for snippet in required_markup:
        assert snippet in HTML
    assert "Edit / Reset Password" in SCRIPT
    assert "Leave blank to keep the current password." in SCRIPT
    assert "Password is required for new users." in SCRIPT
    assert "if (!isEdit || password) payload.password = password;" in SCRIPT


def test_admin_portal_navigation_is_admin_only() -> None:
    assert "function canManageUsers()" in SCRIPT
    assert "db.currentUser?.role === 'admin'" in SCRIPT
    assert "document.querySelectorAll('[data-admin-only]')" in SCRIPT
    assert "Your role is not allowed to manage users." in SCRIPT
    assert HTML.count("data-admin-only") >= 3
