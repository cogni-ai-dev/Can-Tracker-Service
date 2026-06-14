# Plan 07: MFU Import And Sync

## Goal

Implement fixed-template CSV/XLSX import for MFU-related client data and define an adapter boundary for future direct MFU API sync.

## Context

The selected integration strategy is hybrid import plus future API. The v1 backend should support daily staff uploads using a fixed template, validate rows before commit, preserve manual local data, and audit every committed change. Direct MFU API integration is deferred until API documentation, credentials, and sandbox access are available.

## In Scope

- Fixed-template CSV/XLSX upload.
- Row parsing and normalization.
- Validation preview.
- Import batch and row tracking.
- Commit flow.
- Conflict detection.
- Merge rules for existing families and members.
- Import-sourced audit records.
- `MfuGateway` interface for future API implementation.

## Out Of Scope

- Direct MFU API implementation.
- Scheduled sync jobs.
- Automatic email notifications.
- Arbitrary column mapping.
- User-defined import templates.

## Design

### Fixed Template Columns

Required template headers:

- `FamilyCode`
- `FamilyHeadName`
- `PrimaryRMEmail`
- `PrimaryRMName`
- `FamilyRemarks`
- `MemberName`
- `CANNumber`
- `PAN`
- `DateOfBirth`
- `KYCStatus`
- `Mobile`
- `MobileStatus`
- `Email`
- `EmailStatus`
- `NomineeStatus`
- `BankName`
- `AccountNumber`
- `IFSC`
- `PayEezzStatus`
- `PayEezzAmount`
- `PayEezzStartDate`
- `Remarks`

Required per row:

- `FamilyCode`
- `FamilyHeadName`
- `PrimaryRMEmail` or `PrimaryRMName`
- `MemberName`
- `CANNumber`
- `KYCStatus`
- `MobileStatus`
- `EmailStatus`
- `NomineeStatus`
- `PayEezzStatus`

### Import Tables

`import_batches`:

- `id`
- `file_name`
- `file_sha256`
- `uploaded_by_user_id`
- `status`: `uploaded`, `validated`, `committed`, `failed`
- `row_count`
- `valid_row_count`
- `error_row_count`
- `committed_row_count`
- `created_at`
- `committed_at`

`import_rows`:

- `id`
- `import_batch_id`
- `row_number`
- `raw_data`
- `normalized_data`
- `status`: `valid`, `error`, `conflict`, `committed`, `skipped`
- `errors`
- `family_id`
- `member_id`
- `created_at`

### Endpoints

- `POST /api/v1/imports/mfu-template/upload`
- `GET /api/v1/imports/{batch_id}`
- `GET /api/v1/imports/{batch_id}/rows`
- `POST /api/v1/imports/{batch_id}/commit`
- `GET /api/v1/imports`

### Validation Rules

- Unknown headers fail the batch only if required headers are missing; extra columns can be ignored with a warning.
- Enum values must exactly match canonical labels after trimming whitespace.
- PAN is normalized uppercase and validated if present.
- IFSC is normalized uppercase and validated if present.
- Dates must use `YYYY-MM-DD`.
- PayEezz amount must be numeric and non-negative if present.
- `PrimaryRMEmail`, if present, must match an active RM user.
- If only `PrimaryRMName` is present, match exactly one active RM by name.
- Duplicate CAN numbers inside the same file are row errors.
- Existing CAN under a different family is a conflict and is not committed.

### Merge Rules

Family matching:

- Match by `FamilyCode`.
- Create family if no active family exists.
- Update `family_head_name` and `primary_rm_id` from import.
- Preserve local family `remarks` unless `FamilyRemarks` is non-empty.

Member matching:

- Match by `CANNumber`.
- Create member if no active member exists.
- Update MFU-origin fields from import.
- Preserve local remarks unless `Remarks` is non-empty.
- Preserve family assignment unless member is new. Existing CAN under a different family is a conflict.

Audit:

- Every committed create or update creates audit rows with source `import`.
- Every audit row links to `import_batch_id`.
- Conflicted and error rows do not mutate business records.

### Future MFU API Boundary

Create an interface:

```text
MfuGateway
  fetch_members_since(timestamp) -> iterable[MfuMemberRecord]
  fetch_member_by_can(can_number) -> MfuMemberRecord | None
```

V1 implementation:

- `TemplateMfuGateway`, used by upload and commit flow.

Future implementation:

- `ApiMfuGateway`, behind the same normalized record contract.

## Implementation Steps

1. Add import batch and row models.
2. Add parser for CSV and XLSX.
3. Add template header validation.
4. Add row normalization and validation service.
5. Add upload endpoint that stores batch and row validation results.
6. Add row preview endpoints with pagination and status filters.
7. Add commit endpoint using one database transaction per batch or controlled row chunks.
8. Add merge logic with audit integration.
9. Add `MfuGateway` interface and `TemplateMfuGateway`.
10. Add tests with valid rows, errors, conflicts, and duplicate rows.

## Subagent Usage

- Use `cavecrew-investigator` to inspect member CRUD services and audit service before implementing import commit.
- Use the main thread for parser, validation, merge, and transaction design because mistakes can corrupt data.
- Use `cavecrew-reviewer` to audit conflict handling, audit coverage, and preservation of local fields.
- Use `cavecrew-builder` only for targeted fixes to parser tests or a single validation helper.

## Test Plan

- Upload accepts valid CSV.
- Upload accepts valid XLSX.
- Missing required header creates batch validation failure.
- Invalid enum values create row errors.
- Invalid PAN, IFSC, date, and amount create row errors.
- Duplicate CAN inside file creates row errors.
- Existing CAN under same family updates member.
- Existing CAN under different family creates conflict and does not update.
- New family and new member are created on commit.
- Import preserves local remarks when template remarks are empty.
- Import audit rows include source `import` and batch id.
- Commit is idempotent by rejecting already committed batches.

## Acceptance Criteria

- Operations can upload a fixed MFU template, review row status, and commit valid rows.
- No invalid or conflicted row mutates family/member data.
- Every import mutation is field-level audited.
- Import behavior uses the same enum and validation rules as manual CRUD.
- Future direct MFU API sync can reuse normalized record and merge services.

## Risks & Mitigations

- Risk: MFU export format differs from template. Mitigation: keep v1 fixed-template and add mapping only after seeing real samples.
- Risk: large imports time out. Mitigation: validate in batches and add background jobs later if needed.
- Risk: commits partially apply. Mitigation: use clear transaction policy and store row commit status.

## Dependencies

- [04-pii-security-and-audit.md](04-pii-security-and-audit.md)
- [05-family-member-crud-apis.md](05-family-member-crud-apis.md)

