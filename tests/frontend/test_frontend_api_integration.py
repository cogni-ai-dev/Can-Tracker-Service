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
