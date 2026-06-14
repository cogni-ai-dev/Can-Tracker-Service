# MFU CAN Tracker Backend Master Plan

## Objective

Build a production-ready backend for a family-wise CAN tracker used by a Mutual Fund Distribution business that uses MFU as the transaction backend. The backend must persist client family data, CAN-level compliance data, KYC status, PayEezz status, contact verification, nominee verification, computed pending tasks, exports, imports, and a complete audit trail.

The current repository contains a generated standalone HTML dashboard. That HTML is the v1 product baseline. It stores data in an in-memory JavaScript object and calculates counters, task lists, and report rows in the browser. The backend must preserve the same business behavior while moving persistence, security, audit, reporting, and integration logic to server-side APIs.

## Architecture Summary

- Backend stack: FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL.
- Deployment target: Docker Compose on a cloud VM for v1.
- Frontend target: keep the generated HTML experience initially and replace the in-memory `db` with API calls.
- Auth model: one distributor firm with role-based users.
- Roles: `admin`, `ops`, `rm`, `management`.
- Data model: one family has many members; one member equals one CAN in v1.
- Bank and PayEezz model: one active bank record and one active PayEezz state per member.
- Task model: pending tasks are computed from member statuses, not stored as independent task records.
- MFU integration: fixed-template CSV/XLSX import first, with a service interface for future direct MFU API sync.
- Security: encrypt PAN, mobile, email, and bank account values at rest; return masked values unless the actor can view sensitive data.
- Audit: field-level audit log for manual edits, imports, and future MFU API sync.

## Shared Vocabulary

Use these exact enum labels in database constraints, API validation, imports, reports, and frontend integration unless a future migration intentionally changes them.

### KYC Status

- `Validated`: compliant.
- `Registered`: re-KYC pending.
- `No KYC`: KYC pending.

KYC pending means `Registered` plus `No KYC`.

### Verification Status

- `Verified`
- `Not Verified`

This enum applies to mobile verification, email verification, and nominee verification.

### PayEezz Status

- `Not Available`
- `Sent for Approval`
- `Aggregator Accepted`

PayEezz pending means `Not Available` plus `Sent for Approval`.

### Task Types

- `kyc`
- `payeezz`
- `mobile`
- `email`
- `nominee`

### Report Types

- `kyc_pending`
- `payeezz_pending`
- `contact_pending`
- `family_compliance`
- `rm_tasks`
- `full`

### Change Sources

- `manual`
- `import`
- `mfu_api`

## API Conventions

- All backend routes live under `/api/v1`.
- Use snake_case JSON field names.
- Use UUID primary keys in API responses.
- Use UTC ISO 8601 timestamps with timezone.
- Paginated list responses use `items`, `total`, `limit`, `offset`.
- Errors use a consistent shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Human-readable summary",
    "details": []
  }
}
```

## Milestone Map

| Plan | Purpose | Depends On |
| --- | --- | --- |
| [01-domain-model-and-business-rules.md](01-domain-model-and-business-rules.md) | Defines the domain, statuses, computed formulas, tasks, and report semantics. | None |
| [02-backend-foundation.md](02-backend-foundation.md) | Creates the FastAPI/Postgres project foundation. | 01 |
| [03-auth-rbac-and-users.md](03-auth-rbac-and-users.md) | Adds login, sessions, roles, users, and RM visibility. | 01, 02 |
| [04-pii-security-and-audit.md](04-pii-security-and-audit.md) | Adds encryption, masking, searchable hashes, and field-level audit. | 01, 02, 03 |
| [05-family-member-crud-apis.md](05-family-member-crud-apis.md) | Adds family/member CRUD, search, filters, validation, and soft deletes. | 01, 02, 03, 04 |
| [06-dashboard-and-computed-tasks.md](06-dashboard-and-computed-tasks.md) | Adds dashboard summaries, family compliance, and task endpoints. | 05 |
| [07-mfu-import-and-sync.md](07-mfu-import-and-sync.md) | Adds fixed-template imports and future MFU sync adapter boundaries. | 05, 04 |
| [08-reporting-and-exports.md](08-reporting-and-exports.md) | Adds CSV/XLSX/PDF reports and export audit. | 06, 07 |
| [09-frontend-api-integration.md](09-frontend-api-integration.md) | Replaces in-memory frontend data with API calls. | 05, 06, 08 |
| [10-deployment-operations-and-quality.md](10-deployment-operations-and-quality.md) | Adds deployment, backups, observability, release gates, and QA workflow. | 02 through 09 |

## Dependency Order

1. Domain rules must land before schemas and endpoints.
2. Backend foundation must land before auth, audit, CRUD, reports, and imports.
3. Auth and roles must land before any endpoint returns sensitive or scoped data.
4. PII and audit must land before real member CRUD is exposed to operations users.
5. CRUD must land before dashboard, tasks, imports, and reports.
6. Dashboard and task endpoints must land before frontend integration.
7. Imports can start after CRUD and audit are stable.
8. Reports can start after dashboard formulas and import semantics are stable.
9. Deployment work should harden the system after the API surface is coherent.

## Subagent Policy

Use subagents to improve quality where the work is bounded and the output can be verified.

- Use `cavecrew-investigator` before changing an existing area to map routes, models, tests, fixtures, and call sites.
- Use parallel `cavecrew-investigator` passes for broad milestones: one for schema/API, one for tests, and one for frontend touchpoints.
- Use `cavecrew-builder` only for surgical edits in one or two known files.
- Do not use `cavecrew-builder` for migrations, cross-cutting schema decisions, or multi-file feature work.
- Use `cavecrew-reviewer` after each milestone diff to catch regressions, missing tests, authorization gaps, and contract mismatches.
- Keep architecture decisions, migrations, security model, and multi-file implementation in the main thread.

## Risk Register

| Risk | Impact | Mitigation |
| --- | --- | --- |
| MFU API details are unavailable | Direct sync cannot be built accurately | Ship fixed-template import first and isolate future API work behind `MfuGateway`. |
| PII leakage through logs or responses | Compliance and client trust risk | Encrypt at rest, mask by default, redact logs, test role-based sensitive access. |
| Dashboard formulas diverge from UI | Management sees inconsistent compliance numbers | Centralize formula functions and test every status combination. |
| Imports overwrite manual corrections | Operations loses local context | Merge MFU-origin fields only, preserve local-only fields, audit conflicts. |
| Audit trail becomes noisy or incomplete | Hard to investigate changes | Use field-level diffs, source labels, import batch links, and actor attribution. |
| Report exports become slow | Management and ops workflow degrades | Use indexed queries, stream large exports, add saved jobs only if on-demand exports become too slow. |

## Global Acceptance Criteria

- The backend can persist all family and member fields currently present in the generated HTML.
- All dashboard counters and task lists match the formulas in this plan.
- All writes create field-level audit entries with actor and source.
- Sensitive fields are encrypted at rest and masked by default in API responses.
- Admin, Ops, RM, and Management roles have enforced endpoint permissions.
- Fixed-template MFU import supports validate, preview, commit, and conflict reporting.
- Reports export CSV, XLSX, and PDF for all required report types.
- The generated HTML can be incrementally adapted to use the backend APIs.

