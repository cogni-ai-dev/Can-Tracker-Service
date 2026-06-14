# Implementation Prompts For MFU CAN Tracker Backend Plans

Use these prompts sequentially. Start with Prompt 00, then run Prompt 01 through Prompt 10 in order. Each prompt assumes the agent is working in the repository root:

```text
/Users/oxygen/work/personal/repos/Can-Tracker-Service
```

General operating rules for every prompt:

- Read the referenced plan and dependencies before editing.
- Preserve existing user changes.
- Use `rg` for search.
- Use `apply_patch` for manual edits.
- Do not skip tests unless blocked; if blocked, explain the exact blocker.
- Use subagents only where the plan says they improve quality.
- End with changed files, tests run, and remaining risks.

## Prompt 00: Project Orientation And Plan Consistency

```text
You are implementing the MFU CAN Tracker backend planning pack.

First, read:
- docs/plans/00-master-backend-plan.md
- docs/plans/01-domain-model-and-business-rules.md
- docs/plans/02-backend-foundation.md
- docs/plans/03-auth-rbac-and-users.md
- docs/plans/04-pii-security-and-audit.md
- docs/plans/05-family-member-crud-apis.md
- docs/plans/06-dashboard-and-computed-tasks.md
- docs/plans/07-mfu-import-and-sync.md
- docs/plans/08-reporting-and-exports.md
- docs/plans/09-frontend-api-integration.md
- docs/plans/10-deployment-operations-and-quality.md

Do not implement product code in this prompt.

Your task:
1. Inspect the repo state.
2. Verify the plans are internally consistent.
3. Identify any missing implementation prerequisites.
4. Produce an execution checklist for Prompt 01 through Prompt 10.

Use cavecrew-investigator only if the repo already contains backend files that need mapping. Otherwise work in the main thread.

Final response must include:
- Confirmed implementation order.
- Any plan contradictions found.
- Any prerequisites before Prompt 01.
- No code changes unless you find and fix a documentation typo or contradiction.
```

## Prompt 01: Domain Model And Business Rules

```text
Implement docs/plans/01-domain-model-and-business-rules.md from start to finish.

Before editing, read:
- docs/plans/00-master-backend-plan.md
- docs/plans/01-domain-model-and-business-rules.md
- remixed-c3e65622.html

Goal:
Create the canonical domain layer for enums, compliance formulas, task generation, and report definitions. Do not create database models or API routes in this prompt.

Implementation requirements:
1. Add the backend project files needed only for the domain layer if the backend scaffold does not exist yet.
2. Define canonical enum labels exactly as the plan specifies.
3. Implement pure calculation helpers for:
   - KYC counts and percentages.
   - PayEezz counts and percentages.
   - Mobile, email, and nominee verification counts and percentages.
   - Family completion percentages.
   - Zero-denominator behavior.
4. Implement computed task generation from member-like records.
5. Implement report definition metadata for all report types.
6. Add focused tests for every enum, formula, task rule, and report filter.

Subagent use:
- Use cavecrew-investigator to inspect the current HTML calculations and report/task logic.
- Keep final domain design in the main thread.
- Use cavecrew-reviewer after the diff is ready.

Verification:
- Run the relevant test suite.
- If no test runner exists yet, add the minimal test runner needed for this domain work.

Final response:
- Summarize changed files.
- List tests run and results.
- Note any deliberate deferrals to Prompt 02.
```

## Prompt 02: Backend Foundation

```text
Implement docs/plans/02-backend-foundation.md from start to finish.

Before editing, read:
- docs/plans/00-master-backend-plan.md
- docs/plans/01-domain-model-and-business-rules.md
- docs/plans/02-backend-foundation.md

Goal:
Create the FastAPI, SQLAlchemy, Alembic, PostgreSQL, Docker, settings, health-check, and test foundation.

Implementation requirements:
1. Add Python dependency/project configuration.
2. Create the planned app layout.
3. Preserve or move the domain code from Prompt 01 into the planned layout without changing behavior.
4. Implement settings with required environment variables and test-safe defaults.
5. Implement SQLAlchemy engine/session/base and Alembic configuration.
6. Add API router structure under /api/v1.
7. Add GET /health, GET /ready, and GET /api/v1/meta.
8. Add Dockerfile and Docker Compose for API and Postgres.
9. Add pytest configuration, test database strategy, and health/readiness tests.
10. Update README with local backend commands.

Subagent use:
- Use the main thread for the scaffold because it spans many files.
- Use cavecrew-reviewer after the foundation diff is complete.
- Use cavecrew-builder only for small post-review fixes.

Verification:
- Run formatter/linter if configured.
- Run tests.
- Run an Alembic migration smoke check.
- If Docker is available, validate Docker Compose startup enough to confirm config.

Final response:
- Summarize changed files.
- List exact commands run and results.
- Identify any environment values the user must provide.
```

## Prompt 03: Auth, RBAC, And Users

```text
Implement docs/plans/03-auth-rbac-and-users.md from start to finish.

Before editing, read:
- docs/plans/00-master-backend-plan.md
- docs/plans/01-domain-model-and-business-rules.md
- docs/plans/02-backend-foundation.md
- docs/plans/03-auth-rbac-and-users.md

Goal:
Add email/password auth, sessions, user model, roles, user management APIs, RM listing, and reusable authorization dependencies.

Implementation requirements:
1. Add UserRole enum with admin, ops, rm, management.
2. Add users model and migration.
3. Add password hashing.
4. Add login, logout, and /auth/me.
5. Add user management endpoints for Admin.
6. Add GET /api/v1/rms.
7. Add reusable dependencies for authenticated user, role checks, active user checks, and future RM scoping.
8. Add local bootstrap admin flow that does not hardcode credentials.
9. Add tests for auth success/failure, inactive users, role restrictions, and anonymous access.

Subagent use:
- Use cavecrew-investigator to map current route structure before adding auth.
- Use the main thread for session and authorization design.
- Use cavecrew-reviewer to audit missing guards and inactive-user bypasses.

Verification:
- Run migrations.
- Run auth/user tests.
- Run the full current test suite.

Final response:
- Summarize changed files.
- List test commands and results.
- Note how to create the first admin user.
```

## Prompt 04: PII Security And Audit

```text
Implement docs/plans/04-pii-security-and-audit.md from start to finish.

Before editing, read:
- docs/plans/00-master-backend-plan.md
- docs/plans/01-domain-model-and-business-rules.md
- docs/plans/02-backend-foundation.md
- docs/plans/03-auth-rbac-and-users.md
- docs/plans/04-pii-security-and-audit.md

Goal:
Add PII encryption/masking/search hashes and field-level audit logging.

Implementation requirements:
1. Add encryption helpers for PAN, mobile, email, and bank account values.
2. Add deterministic HMAC search hash helpers.
3. Add masking helpers for PAN, mobile, email, and bank account numbers.
4. Add audit_logs model and migration.
5. Add audit service for create, update, delete, sensitive_read, import_commit.
6. Add field-level diff logic with masked values for sensitive fields.
7. Ensure audit writes participate in the same transaction as business writes.
8. Add log redaction for sensitive fields.
9. Add protected audit query endpoint if enough auth infrastructure exists.
10. Add tests proving no plaintext PII persistence and correct audit behavior.

Subagent use:
- Use cavecrew-investigator to find serializers/routes where sensitive data could leak.
- Use the main thread for encryption, audit, and transaction boundaries.
- Use cavecrew-reviewer focused on leaks, missing audit rows, and transaction gaps.

Verification:
- Run security/audit tests.
- Run full test suite.
- If database models exist, inspect generated migration for sensitive column names and indexes.

Final response:
- Summarize changed files.
- List tests run and results.
- State exactly which fields are encrypted and how full-value reads are controlled.
```

## Prompt 05: Family And Member CRUD APIs

```text
Implement docs/plans/05-family-member-crud-apis.md from start to finish.

Before editing, read:
- docs/plans/00-master-backend-plan.md
- docs/plans/01-domain-model-and-business-rules.md
- docs/plans/03-auth-rbac-and-users.md
- docs/plans/04-pii-security-and-audit.md
- docs/plans/05-family-member-crud-apis.md

Goal:
Add durable family and member CRUD APIs with validation, search, filters, soft deletes, PII masking, role access, and audit.

Implementation requirements:
1. Add families and members models and migrations.
2. Add Pydantic schemas for create, update, detail, list, and paginated responses.
3. Add repository/query helpers.
4. Add service layer with validation, PII handling, and audit integration.
5. Add family endpoints:
   - GET /api/v1/families
   - POST /api/v1/families
   - GET /api/v1/families/{family_id}
   - PATCH /api/v1/families/{family_id}
   - DELETE /api/v1/families/{family_id}
   - GET /api/v1/families/{family_id}/members
   - POST /api/v1/families/{family_id}/members
6. Add member endpoints:
   - GET /api/v1/members
   - GET /api/v1/members/{member_id}
   - PATCH /api/v1/members/{member_id}
   - DELETE /api/v1/members/{member_id}
7. Implement filters for KYC, PayEezz, mobile, email, nominee, RM, family, and search.
8. Enforce RM visibility at query level.
9. Add tests for validation, roles, search, filters, masking, audit, and soft delete.

Subagent use:
- Use parallel cavecrew-investigator passes for models/migrations, route patterns, and tests.
- Keep schema and service design in the main thread.
- Use cavecrew-reviewer for missing role checks, audit gaps, and sensitive-field leaks.
- Use cavecrew-builder only for small endpoint/schema fixes after the main implementation.

Verification:
- Run migrations.
- Run CRUD/API tests.
- Run full test suite.

Final response:
- Summarize changed files.
- List API endpoints implemented.
- List tests run and results.
- Note any frontend-facing response contract details.
```

## Prompt 06: Dashboard And Computed Tasks

```text
Implement docs/plans/06-dashboard-and-computed-tasks.md from start to finish.

Before editing, read:
- docs/plans/00-master-backend-plan.md
- docs/plans/01-domain-model-and-business-rules.md
- docs/plans/05-family-member-crud-apis.md
- docs/plans/06-dashboard-and-computed-tasks.md
- remixed-c3e65622.html

Goal:
Add dashboard summary, family summary, task list, and task summary endpoints using persisted data and canonical formulas.

Implementation requirements:
1. Add dashboard query service.
2. Add GET /api/v1/dashboard/summary.
3. Add GET /api/v1/dashboard/families/{family_id}.
4. Add computed task query/generation service.
5. Add GET /api/v1/tasks.
6. Add GET /api/v1/tasks/summary.
7. Implement RM scoping and optional RM filters.
8. Implement pagination and deterministic task ordering.
9. Reuse domain formulas from Prompt 01.
10. Add tests for all counters, percentages, task types, filters, empty data, and RM scoping.

Subagent use:
- Use cavecrew-investigator to compare frontend calculations in remixed-c3e65622.html.
- Use the main thread for aggregate query design and scoping.
- Use cavecrew-reviewer to check formula parity, RM scoping, and pagination.

Verification:
- Run dashboard/task tests.
- Run full test suite.
- Compare one mixed fixture manually against expected HTML-style calculations.

Final response:
- Summarize changed files.
- List endpoints implemented.
- List tests run and results.
- Note any performance indexes added or deferred.
```

## Prompt 07: MFU Import And Sync

```text
Implement docs/plans/07-mfu-import-and-sync.md from start to finish.

Before editing, read:
- docs/plans/00-master-backend-plan.md
- docs/plans/01-domain-model-and-business-rules.md
- docs/plans/04-pii-security-and-audit.md
- docs/plans/05-family-member-crud-apis.md
- docs/plans/07-mfu-import-and-sync.md

Goal:
Add fixed-template CSV/XLSX MFU import with validation preview, row tracking, commit, merge rules, conflict handling, audit, and a future MFU gateway interface.

Implementation requirements:
1. Add import_batches and import_rows models and migrations.
2. Add parser support for CSV and XLSX.
3. Validate required headers from the fixed template.
4. Normalize and validate each row.
5. Add upload endpoint:
   - POST /api/v1/imports/mfu-template/upload
6. Add preview/list endpoints:
   - GET /api/v1/imports
   - GET /api/v1/imports/{batch_id}
   - GET /api/v1/imports/{batch_id}/rows
7. Add commit endpoint:
   - POST /api/v1/imports/{batch_id}/commit
8. Implement merge rules exactly from the plan.
9. Add MfuGateway interface and TemplateMfuGateway implementation.
10. Add import-sourced audit rows with import_batch_id.
11. Add tests for valid files, bad headers, invalid rows, duplicate CANs, conflicts, successful commit, idempotency, and audit.

Subagent use:
- Use cavecrew-investigator to inspect CRUD and audit services before commit logic.
- Use the main thread for parser, validation, merge, and transaction design.
- Use cavecrew-reviewer for conflict handling, audit coverage, and local-field preservation.
- Use cavecrew-builder only for small parser or validation helper fixes.

Verification:
- Run import tests.
- Run full test suite.
- Manually verify a committed import changes expected records and leaves conflicted rows untouched.

Final response:
- Summarize changed files.
- List endpoints implemented.
- List tests run and results.
- State the exact template columns supported.
```

## Prompt 08: Reporting And Exports

```text
Implement docs/plans/08-reporting-and-exports.md from start to finish.

Before editing, read:
- docs/plans/00-master-backend-plan.md
- docs/plans/01-domain-model-and-business-rules.md
- docs/plans/06-dashboard-and-computed-tasks.md
- docs/plans/07-mfu-import-and-sync.md
- docs/plans/08-reporting-and-exports.md

Goal:
Add on-demand CSV, XLSX, and PDF exports for all required report types, with role scoping, masked sensitive fields, and export audit.

Implementation requirements:
1. Add report_exports model and migration.
2. Add report definition registry for:
   - kyc_pending
   - payeezz_pending
   - contact_pending
   - family_compliance
   - rm_tasks
   - full
3. Add role-scoped query builders.
4. Add CSV renderer.
5. Add XLSX renderer.
6. Add PDF renderer.
7. Add preview endpoint:
   - GET /api/v1/reports/{report_type}/preview
8. Add export endpoint:
   - GET /api/v1/reports/{report_type}/export
9. Record report_exports rows for successful exports.
10. Add tests for every report type, every format, masking, RM scoping, invalid formats, and export audit.

Subagent use:
- Use cavecrew-investigator to inspect dashboard/task query services before report query work.
- Use the main thread for report definitions and role scoping.
- Use cavecrew-builder for isolated renderer fixes.
- Use cavecrew-reviewer for report filters, masking, scoping, and export audit.

Verification:
- Run report/export tests.
- Run full test suite.
- Open or validate generated XLSX/PDF files in tests where practical.

Final response:
- Summarize changed files.
- List report types and formats implemented.
- List tests run and results.
- Note any PDF row-limit behavior.
```

## Prompt 09: Frontend API Integration

```text
Implement docs/plans/09-frontend-api-integration.md from start to finish.

Before editing, read:
- docs/plans/00-master-backend-plan.md
- docs/plans/05-family-member-crud-apis.md
- docs/plans/06-dashboard-and-computed-tasks.md
- docs/plans/08-reporting-and-exports.md
- docs/plans/09-frontend-api-integration.md
- remixed-c3e65622.html

Goal:
Replace the generated HTML's in-memory data flow with backend API calls while preserving the current v1 UI and workflows.

Implementation requirements:
1. Add a small API client wrapper.
2. Add auth check on page load.
3. Disable or remove production dependence on seedData.
4. Convert dashboard rendering to backend summary and task APIs.
5. Convert family list, filters, and detail views to backend APIs.
6. Convert add/edit/delete family/member flows to backend APIs.
7. Convert KYC, PayEezz, contact, and task tabs to backend filters.
8. Convert report preview and download buttons to backend report endpoints.
9. Add loading, empty, and error states.
10. Add browser or integration checks for major screens.

Subagent use:
- Use cavecrew-investigator to map every db usage and render function.
- Use cavecrew-builder for one or two known function conversions at a time.
- Use the main thread for API client design and cross-page state.
- Use cavecrew-reviewer after each integration slice to catch stale db references and broken filters.

Verification:
- Run backend tests.
- Run frontend/browser checks if available.
- Search for remaining production db/seedData dependencies.
- Manually exercise dashboard, families, member update, tasks, and reports if a dev server/browser is available.

Final response:
- Summarize changed files.
- List screens integrated.
- List tests/checks run and results.
- Note any UI flows still using mock data.
```

## Prompt 10: Deployment, Operations, And Quality

```text
Implement docs/plans/10-deployment-operations-and-quality.md from start to finish.

Before editing, read:
- docs/plans/00-master-backend-plan.md
- docs/plans/02-backend-foundation.md
- docs/plans/03-auth-rbac-and-users.md
- docs/plans/04-pii-security-and-audit.md
- docs/plans/05-family-member-crud-apis.md
- docs/plans/06-dashboard-and-computed-tasks.md
- docs/plans/07-mfu-import-and-sync.md
- docs/plans/08-reporting-and-exports.md
- docs/plans/09-frontend-api-integration.md
- docs/plans/10-deployment-operations-and-quality.md

Goal:
Harden the app for Docker-based cloud VM deployment with production config, backups, restore documentation, observability, release gates, and QA workflow.

Implementation requirements:
1. Harden Dockerfile and Compose configuration for production.
2. Add .env.example with placeholders only.
3. Add or verify production settings validation.
4. Add structured logging and request id middleware if not already present.
5. Add backup script and restore procedure documentation.
6. Add initial deployment runbook.
7. Add first-admin creation runbook.
8. Add import failure and report export troubleshooting runbooks.
9. Add release checklist with tests, migrations, security checks, imports, reports, and review gates.
10. Run final consistency and security review.

Subagent use:
- Use cavecrew-investigator for config, tests, and docs mapping.
- Use the main thread for production security, backup, and release decisions.
- Use cavecrew-builder for narrow script/doc edits once paths are known.
- Use cavecrew-reviewer for final diff review focused on secrets, exposed ports, missing backup steps, and broken commands.

Verification:
- Run full test suite.
- Run migration smoke checks.
- Validate Docker production build if Docker is available.
- Validate backup command syntax and restore documentation.
- Confirm no secrets are committed.

Final response:
- Summarize changed files.
- List deployment commands/checks run and results.
- State remaining production prerequisites.
- Confirm release checklist status.
```

## Final End-To-End Verification Prompt

```text
Run final end-to-end verification for the MFU CAN Tracker backend project.

Read:
- docs/plans/00-master-backend-plan.md
- docs/plans/10-deployment-operations-and-quality.md

Task:
1. Inspect repo status and recent changes.
2. Run the full test suite.
3. Run migrations against a clean test database if possible.
4. Run lint/format checks if configured.
5. Run import/export focused tests.
6. Run auth/RBAC and PII/audit focused tests.
7. If frontend integration exists, start the app and browser-check dashboard, families, member edit, tasks, and reports.
8. Search for secrets, plaintext PII logging, remaining mock-data dependencies, and TODOs that block release.
9. Produce a concise release-readiness report.

Use cavecrew-reviewer for final diff review if there are unreviewed code changes.

Final response must include:
- Pass/fail status.
- Commands run.
- Blockers.
- Non-blocking risks.
- Recommended next action.
```

