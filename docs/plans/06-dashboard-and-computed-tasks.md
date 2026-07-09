# Plan 06: Dashboard And Computed Tasks

## Goal

Implement API endpoints for real-time dashboard counters, family compliance summaries, RM-filtered metrics, and computed pending task lists.

## Context

The generated HTML calculates KPI cards, charts, family compliance bars, sidebar badges, and task lists from browser memory. The backend should calculate the same values from persisted active records and return compact, frontend-ready responses.

## In Scope

- Global dashboard summary endpoint.
- RM-filtered dashboard summary.
- Family dashboard summary.
- Contact, KYC, PayEezz, nominee counters.
- Computed task list endpoint.
- Task count summaries by type.
- Pagination and filters for task lists.
- Performance indexes or aggregate query strategy.

## Out Of Scope

- Storing task records.
- Task assignment, due dates, reminders, or snoozing.
- Saved dashboard snapshots.
- Scheduled management reports.

## Design

### Endpoints

- `GET /api/v1/dashboard/summary`
- `GET /api/v1/dashboard/families/{family_id}`
- `GET /api/v1/tasks`
- `GET /api/v1/tasks/summary`

### Dashboard Summary Filters

`GET /api/v1/dashboard/summary` supports:

- `rm_id`: optional; Admin, Ops, and Management only.
- current RM users are automatically scoped to their own assigned families.

### Global Summary Response

Return:

- `total_clients`
- `total_families`
- `kyc_verified`
- `kyc_pending_rekyc`
- `kyc_not_started`
- `kyc_pending`
- `kyc_verified_pct`
- `kyc_pending_pct`
- `payeezz_approved`
- `payeezz_pending_approval`
- `payeezz_not_started`
- `payeezz_pending`
- `payeezz_approved_pct`
- `payeezz_pending_pct`
- `mobile_verified`
- `mobile_pending_verification`
- `email_verified`
- `email_pending_verification`
- `nominee_verified`
- `nominee_pending_verification`
- `updated_at`

### Family Summary Response

Return:

- family fields: id, code, head name, RM, remarks, last updated.
- `number_of_members`
- `total_cans`
- `kyc_completion_pct`
- `mobile_verification_pct`
- `email_verification_pct`
- `nominee_verification_pct`
- `payeezz_completion_pct`
- member table rows using the member response contract from Plan 05.

### Task List Response

`GET /api/v1/tasks` supports:

- `type`: optional, one of task types.
- `rm_id`: optional for Admin, Ops, Management.
- `family_id`
- `q`
- `priority`
- `limit`
- `offset`

The endpoint returns computed task rows from current member status fields. Each pending status on a member produces a separate task row.

### Performance Strategy

For v1 scale of hundreds of families and thousands of CANs:

- Use indexed status columns.
- Use SQL aggregate queries for counters.
- Use server-side pagination for task lists.
- Avoid loading all members into Python for dashboard summaries.
- Keep task generation as queryable derived rows where possible. If implemented in Python, limit it to paginated candidate rows and keep summary counts in SQL.

## Implementation Steps

1. Add dashboard query service with shared formula functions from Plan 01.
2. Implement global summary query.
3. Implement RM scoping in summary queries.
4. Implement family summary query and member row inclusion.
5. Implement computed task query builder.
6. Implement task summary counts by type.
7. Add route handlers and response schemas.
8. Add integration tests with mixed compliance fixtures.
9. Compare API output against the generated HTML seed-data calculations.

## Subagent Usage

- Use `cavecrew-investigator` to inspect frontend dashboard and task calculations before implementing query logic.
- Use the main thread for aggregate query design and scoping rules.
- Use `cavecrew-reviewer` to check formula parity, RM scoping, and pagination correctness.
- Use `cavecrew-builder` only for small response schema or test fixture corrections.

## Test Plan

- Dashboard returns correct totals for all KYC states.
- Dashboard returns correct totals for all PayEezz states.
- Dashboard returns correct mobile, email, and nominee counts.
- Percentages return `0` for empty data.
- RM dashboard includes only assigned families.
- Family dashboard percentages match member states.
- Task list generates one task per pending status.
- Task filters by type, RM, family, priority, and search.
- Task summary counts match task list totals.
- Management can read dashboard and tasks but cannot mutate records.

## Acceptance Criteria

- Dashboard endpoint can populate all KPI cards in the generated HTML.
- Family summary endpoint can populate the family detail page.
- Task endpoints can populate sidebar badges, top tasks, and pending task tabs.
- All calculations use canonical enum labels and formulas from Plan 01.
- Query performance is acceptable for thousands of members with indexed columns.

## Risks & Mitigations

- Risk: SQL aggregate logic differs from Python formula helpers. Mitigation: test aggregate outputs against formula outputs on fixtures.
- Risk: computed task pagination is inaccurate. Mitigation: use deterministic ordering and count total generated tasks.
- Risk: RM scoping is missed in aggregate queries. Mitigation: add explicit RM tests for every dashboard and task endpoint.

## Dependencies

- [05-family-member-crud-apis.md](05-family-member-crud-apis.md)

