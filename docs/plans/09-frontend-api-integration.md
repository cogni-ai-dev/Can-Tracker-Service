# Plan 09: Frontend API Integration

## Goal

Replace the generated HTML file's in-memory JavaScript data store with calls to the backend APIs while preserving the existing v1 screens and workflows.

## Context

The generated HTML currently seeds demo data, stores it in `db.families` and `db.members`, calculates all counters in the browser, and exports CSV locally. This plan adapts the UI to use backend persistence without redesigning the visual CRM experience.

## In Scope

- API client wrapper.
- Auth-aware page load behavior.
- Family list and filters backed by API.
- Family detail backed by API.
- Member create/update/delete backed by API.
- Dashboard and task pages backed by API.
- Report buttons backed by API export endpoints.
- Loading, empty, and error states.
- Frontend regression checks against current behavior.

## Out Of Scope

- Full React/Vue rewrite.
- Major UI redesign.
- Offline mode.
- Bulk inline editing.
- Browser-side XLSX/PDF generation.

## Design

### Current Frontend Functions To Replace

Replace direct `db` access in:

- `seedData`
- `renderDashboard`
- `renderFamilies`
- `openFamilyDetail`
- `renderKYCPage`
- `renderPayPage`
- `renderContactPage`
- `renderTasksPage`
- `globalSearch`
- `saveFamily`
- `saveMember`
- `deleteMember`
- `generateReport`
- `exportReport`

### API Client

Add a small client layer:

```text
api.get(path, params)
api.post(path, body)
api.patch(path, body)
api.delete(path)
api.download(path, params)
```

Behavior:

- Always call `/api/v1`.
- Include credentials for cookie session.
- Parse JSON errors into UI-safe messages.
- Support request cancellation or stale-response guards for search.

### Screen Mapping

Dashboard page:

- `GET /api/v1/dashboard/summary`
- `GET /api/v1/tasks?limit=8`
- RM dropdown from `GET /api/v1/rms`

Families page:

- `GET /api/v1/families?q=&status_filter=&limit=&offset=`

Family detail page:

- `GET /api/v1/dashboard/families/{family_id}`
- `PATCH /api/v1/families/{family_id}`
- `POST /api/v1/families/{family_id}/members`
- `PATCH /api/v1/members/{member_id}`
- `DELETE /api/v1/members/{member_id}`

KYC page:

- `GET /api/v1/members?kyc_status=...`
- Or a dedicated query through member list filters.

PayEezz page:

- `GET /api/v1/members?payeezz_mandate_status=...`

Contact page:

- `GET /api/v1/members?mobile_verification_status=...`
- `GET /api/v1/members?email_verification_status=...`
- `GET /api/v1/members?nominee_verification_status=...`

Tasks page:

- `GET /api/v1/tasks/summary`
- `GET /api/v1/tasks?type=...`

Reports page:

- `GET /api/v1/reports/{report_type}/preview`
- `GET /api/v1/reports/{report_type}/export?format=csv|xlsx|pdf`

### UI Behavior

- Show loading states in tables and KPI rows.
- Show API error messages without exposing server internals.
- Preserve existing color-coded badges.
- Preserve existing filter labels.
- Keep date formatting compatible with Indian business users.
- Use masked sensitive values returned by backend.

### Authentication Flow

If `/api/v1/auth/me` returns unauthorized:

- Show a minimal login screen or redirect to a login page if one exists.
- After login, load dashboard.

V1 can use a simple login form before a full UI framework exists.

## Implementation Steps

1. Add API client wrapper to the HTML or a separate JS file.
2. Add auth check on page load.
3. Remove or disable `seedData`.
4. Convert dashboard rendering to use backend summary response.
5. Convert family list and detail flows.
6. Convert member save/delete flows.
7. Convert KYC, PayEezz, contact, and task tabs.
8. Convert report preview and export buttons.
9. Add loading and error states.
10. Run browser checks for all major screens.

## Subagent Usage

- Use `cavecrew-investigator` to map every `db.` usage and every render function before editing.
- Use `cavecrew-builder` for one or two known function conversions at a time.
- Use the main thread for API client design and cross-page state handling.
- Use `cavecrew-reviewer` after each integration slice to catch stale `db` references, broken filters, and missing error states.

## Test Plan

- Login flow loads dashboard for an authenticated user.
- Dashboard counters render from backend response.
- Family filters call backend and render expected cards.
- Selecting a family loads members from backend.
- Adding a family persists and appears after reload.
- Editing a member updates dashboard counters and task list.
- Deleting a member soft deletes through backend and removes it from lists.
- KYC, PayEezz, contact, and task tabs call correct filters.
- Report preview and download call backend endpoints.
- Unauthorized API responses return user-friendly UI state.

## Acceptance Criteria

- No production path depends on seeded demo data.
- Refreshing the browser keeps persisted data.
- All existing screens still function.
- All writes go through authenticated backend endpoints.
- Report buttons download server-generated files.
- Sensitive fields displayed in UI are masked unless an explicitly authorized flow is added.

## Risks & Mitigations

- Risk: converting the single HTML file becomes brittle. Mitigation: extract API and render helpers incrementally.
- Risk: old browser calculations conflict with server calculations. Mitigation: treat backend summary responses as authoritative.
- Risk: search causes excessive requests. Mitigation: debounce search input and use server pagination.

## Dependencies

- [05-family-member-crud-apis.md](05-family-member-crud-apis.md)
- [06-dashboard-and-computed-tasks.md](06-dashboard-and-computed-tasks.md)
- [08-reporting-and-exports.md](08-reporting-and-exports.md)

