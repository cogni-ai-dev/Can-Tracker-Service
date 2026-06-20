from pathlib import Path

HTML_PATH = Path(__file__).resolve().parents[2] / "can_tracker_dashboard.html"
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
    assert "Role Access" in HTML
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
        'id="u-can-role"',
        'id="u-txn-role"',
        'id="u-active"',
        'id="u-password"',
        'id="u-password-help"',
    ]
    for snippet in required_markup:
        assert snippet in HTML
    assert "Edit / Reset Password" in SCRIPT
    assert "Leave blank to keep the current password." in SCRIPT
    assert "Password is required for new users." in SCRIPT
    assert "payload.memberships = memberships" in SCRIPT
    assert "Module admins can update module access only." in SCRIPT
    assert "if (!isEdit || password) payload.password = password;" in SCRIPT


def test_admin_role_access_reference_explains_supported_roles() -> None:
    required_text = [
        "Full access",
        "No user management",
        "Assigned families only",
        "remarks-only updates",
        "Read-only access",
        "CRM Admin",
        "Ops / Relationship / Viewer",
    ]
    for text in required_text:
        assert text in HTML


def test_admin_portal_navigation_is_admin_only() -> None:
    assert "function canManageUsers()" in SCRIPT
    assert "db.currentUser?.role === 'admin'" in SCRIPT
    assert "hasModuleRole('client_crm', 'crm_admin')" in SCRIPT
    assert "document.querySelectorAll('[data-admin-only]')" in SCRIPT
    assert "Your role is not allowed to manage users." in SCRIPT
    assert HTML.count("data-admin-only") >= 3


def test_admin_user_management_renders_module_access_controls() -> None:
    required_snippets = [
        "function userAccessBadges",
        "function canAdministerUserModule",
        "function userModuleMembershipPayload",
        "module_code: 'can_compliance'",
        "module_code: 'client_crm'",
        "<th>Access</th>",
    ]
    for snippet in required_snippets:
        assert snippet in HTML or snippet in SCRIPT


def test_client_crm_module_is_in_shared_shell() -> None:
    required_markup = [
        "MFU Operations Portal",
        "navigate('transactions')",
        'id="page-transactions"',
        'id="txn-kpi-row"',
        'id="txn-summary-row"',
        'id="transaction-modal"',
    ]
    for snippet in required_markup:
        assert snippet in HTML


def test_client_crm_uses_local_adapter_until_backend_exists() -> None:
    required_snippets = [
        "const transactionApi =",
        "TRANSACTION_STORAGE_KEY",
        "GET/POST/PATCH/DELETE /api/v1/crm/transactions",
        "GET /api/v1/crm/summary",
        "transactionSeedData()",
        "renderTransactionsPage()",
    ]
    for snippet in required_snippets:
        assert snippet in SCRIPT
    assert "api.get('/transactions'" not in SCRIPT
    assert "api.post('/transactions'" not in SCRIPT
    assert "api.patch('/transactions'" not in SCRIPT
    assert "api.delete('/transactions'" not in SCRIPT
