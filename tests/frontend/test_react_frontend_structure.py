from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
APP = (FRONTEND / "src" / "App.tsx").read_text(encoding="utf-8")
CRM = (FRONTEND / "src" / "modules" / "crm" / "ClientCrmModule.tsx").read_text(encoding="utf-8")
COMPLIANCE = (FRONTEND / "src" / "modules" / "compliance" / "ComplianceModule.tsx").read_text(encoding="utf-8")
ADMIN = (FRONTEND / "src" / "modules" / "admin" / "AdminModule.tsx").read_text(encoding="utf-8")
CRM_API = (FRONTEND / "src" / "modules" / "crm" / "crmMockApi.ts").read_text(encoding="utf-8")
API = (FRONTEND / "src" / "lib" / "api.ts").read_text(encoding="utf-8")
PACKAGE = (FRONTEND / "package.json").read_text(encoding="utf-8")


def test_react_frontend_declares_required_stack() -> None:
    required = [
        '"vite"',
        '"typescript"',
        '"react"',
        '"react-router-dom"',
        '"tailwindcss"',
        '"lucide-react"',
        '"recharts"',
    ]
    for snippet in required:
        assert snippet in PACKAGE


def test_react_app_uses_existing_auth_and_module_access() -> None:
    assert "authApi.me()" in APP
    assert "authApi.login" in APP
    assert "authApi.logout" in APP
    assert "canAccessModule(user, 'can_compliance')" in APP
    assert "canAccessModule(user, 'client_crm')" in APP
    assert "canManageUsers(user)" in APP


def test_react_routes_include_compliance_client_crm_reports_and_admin() -> None:
    required_routes = [
        'path="/compliance/:page"',
        'path="/crm/:page"',
        'path="/reports"',
        'path="/admin/:page"',
        "'/crm/control-centre'",
        "'/compliance/dashboard'",
    ]
    for snippet in required_routes:
        assert snippet in APP


def test_client_crm_skeleton_contains_current_and_future_workflows() -> None:
    required_labels = [
        "Control Centre",
        "Transactions",
        "Redemption Follow-ups",
        "SIP Monitoring",
        "Service Requests",
        "Alerts",
        "Leads",
        "Prospects",
        "Pipeline",
        "Meetings",
        "Relationship Notes",
    ]
    for label in required_labels:
        assert label in CRM


def test_can_compliance_react_module_is_not_placeholder() -> None:
    forbidden_placeholder_labels = [
        "Backend Contract",
        "Summary Fields Loaded",
        "Sample Families Loaded",
        "JSON.stringify(data.tasks",
    ]
    for label in forbidden_placeholder_labels:
        assert label not in COMPLIANCE

    required_workflows = [
        "DashboardPage",
        "FamiliesPage",
        "FamilyDetailPage",
        "KycPage",
        "PayeezzPage",
        "ContactPage",
        "TasksPage",
        "FamilyModal",
        "MemberModal",
        "CanSearch",
        "complianceApi.createFamily",
        "complianceApi.updateMember",
        "complianceApi.deleteMember",
        "complianceApi.exportReport",
    ]
    for snippet in required_workflows:
        assert snippet in COMPLIANCE


def test_client_crm_uses_local_mock_api_until_backend_exists() -> None:
    assert "localStorage" in CRM_API
    assert "crmApi =" in CRM_API
    assert "convertLead" in CRM_API
    assert "GET/POST/PATCH/DELETE /api/v1/crm/transactions" in CRM_API
    assert "GET/POST/PATCH/DELETE /api/v1/crm/service-requests" in CRM_API
    assert "GET/POST/PATCH/DELETE /api/v1/crm/leads" in CRM_API
    assert "GET/POST/PATCH/DELETE /api/v1/crm/prospects" in CRM_API
    assert "GET/POST/PATCH/DELETE /api/v1/crm/pipeline-opportunities" in CRM_API
    assert "GET/POST/PATCH/DELETE /api/v1/crm/meetings" in CRM_API
    assert "GET/POST/PATCH/DELETE /api/v1/crm/notes" in CRM_API
    assert "GET /api/v1/crm/summary" in CRM_API
    assert "GET /api/v1/crm/alerts" in CRM_API
    assert "api.get('/crm" not in API
    assert "api.post('/crm" not in API
    assert "api.patch('/crm" not in API
    assert "api.delete('/crm" not in API


def test_hybrid_lead_to_client_fields_are_present() -> None:
    required_fields = [
        "familyId",
        "memberId",
        "clientId",
        "convertedFamilyId",
        "pending-family-link",
    ]
    combined = CRM_API + (FRONTEND / "src" / "types.ts").read_text(encoding="utf-8")
    for field in required_fields:
        assert field in combined


def test_react_admin_explains_role_access() -> None:
    required_text = [
        "Role Access",
        "Full CAN access, user management, audit logs, imports, and sensitive values.",
        "Create, edit, import, and report across CAN records. No delete, user management, or audit logs.",
        "Assigned families only, with remarks-only updates.",
        "Read-only CAN dashboards, records, tasks, and reports.",
        "Can manage CRM users and CRM module access.",
        "CRM operations work, relationship follow-up, and read-only access labels.",
    ]
    for text in required_text:
        assert text in ADMIN
