# Plan 08: Reporting And Exports

## Goal

Implement on-demand CSV, XLSX, and PDF exports for compliance, pending work, family summaries, RM task summaries, and full CAN database data.

## Context

The generated HTML creates CSV downloads in the browser. The product requirement asks for downloadable Excel, CSV, and PDF reports. Backend exports should use current persisted data, respect role scopes, mask sensitive fields, and record who exported what.

## In Scope

- Report query services.
- CSV export.
- XLSX export.
- PDF export.
- Export audit records.
- Role-scoped report data.
- Report preview metadata if needed by frontend.
- Test fixtures for each report type.

## Out Of Scope

- Scheduled report emails.
- Saved report history with downloadable artifacts.
- Background report jobs for v1.
- Custom report builder.

## Design

### Endpoints

- `GET /api/v1/reports/{report_type}/preview`
- `GET /api/v1/reports/{report_type}/export`

Query parameters:

- `format`: `csv`, `xlsx`, `pdf`.
- `rm_id`: optional where allowed.
- `family_id`: optional where applicable.
- `limit`: preview only.
- `offset`: preview only.

### Export Audit

`report_exports` table:

- `id`
- `report_type`
- `format`
- `filters`
- `row_count`
- `exported_by_user_id`
- `created_at`

Every export creates a `report_exports` row. The audit log can optionally include a summary action, but `report_exports` is the primary export history table.

### Report Types

`kyc_pending`:

- Filter: active members where `kyc_status != Validated`.
- Columns: name, CAN, PAN masked, KYC status, family head, family code, RM, last updated.

`payeezz_pending`:

- Filter: active members where `payeezz_status != Aggregator Accepted`.
- Columns: name, CAN, PayEezz status, bank name, account masked, family head, family code, RM.

`contact_pending`:

- Filter: active members where mobile, email, or nominee status is `Not Verified`.
- Columns: name, CAN, mobile status, email status, nominee status, family head, family code, RM.

`family_compliance`:

- Filter: active families.
- Columns: family head, family code, RM, members, KYC percent, PayEezz percent, mobile percent, email percent, nominee percent.

`rm_tasks`:

- Filter: computed pending tasks grouped by RM.
- Columns: RM, KYC, PayEezz, mobile, email, nominee, total.

`full`:

- Filter: active members.
- Columns: name, CAN, PAN masked, DOB, KYC, mobile status, email status, nominee status, PayEezz, bank name, IFSC, family head, family code, RM, last updated.

### Format Behavior

CSV:

- UTF-8 with BOM if Excel compatibility is needed.
- Proper escaping for commas, quotes, and newlines.

XLSX:

- One worksheet per report.
- Header row frozen.
- Basic column width sizing.
- Dates formatted consistently.

PDF:

- Landscape orientation for wide reports.
- Include report title, generated timestamp, filters, and generated-by user.
- For large datasets, include all rows only if practical. If too large, return a controlled error suggesting CSV/XLSX.

### Access Rules

- Admin, Ops, and Management can export all reports.
- RM can export only assigned family data.
- Sensitive fields remain masked for all v1 report exports.
- Export attempts are logged even when they fail due to validation or authorization if practical.

## Implementation Steps

1. Add `report_exports` model and migration.
2. Add report definition registry using report types from Plan 01.
3. Add query builders that respect role and RM scope.
4. Add CSV renderer.
5. Add XLSX renderer.
6. Add PDF renderer.
7. Add preview endpoint.
8. Add export endpoint with streaming response where appropriate.
9. Add export audit record creation.
10. Add tests for all report types and formats.

## Subagent Usage

- Use `cavecrew-investigator` to inspect dashboard and task query services before writing report queries.
- Use the main thread for report definitions and role scoping.
- Use `cavecrew-builder` for isolated renderer fixes, such as CSV escaping or XLSX header formatting.
- Use `cavecrew-reviewer` to check report filters, role scope, masking, and export audit coverage.

## Test Plan

- Each report type returns expected rows from a mixed fixture.
- CSV escaping handles commas, quotes, and newlines.
- XLSX file opens and contains expected headers and rows.
- PDF export returns a valid PDF content type and includes title metadata.
- RM exports include only assigned families.
- Management can export but cannot mutate data.
- Sensitive report fields are masked.
- Every successful export creates a `report_exports` row.
- Invalid report type returns a controlled error.
- Invalid format returns a controlled error.

## Acceptance Criteria

- All required reports are exportable as CSV, XLSX, and PDF.
- Exported rows match the backend dashboard and task formulas.
- Exports respect role scoping and sensitive-field masking.
- Export history records who exported each report, when, and with which filters.
- The generated HTML report buttons can be wired to these endpoints.

## Risks & Mitigations

- Risk: PDF generation for wide reports is poor. Mitigation: use landscape layout and keep PDF as management preview; recommend XLSX for full data.
- Risk: report queries duplicate dashboard logic. Mitigation: reuse report definitions and formula helpers.
- Risk: large exports use too much memory. Mitigation: stream CSV and add saved background jobs only when needed.

## Dependencies

- [06-dashboard-and-computed-tasks.md](06-dashboard-and-computed-tasks.md)
- [07-mfu-import-and-sync.md](07-mfu-import-and-sync.md)

