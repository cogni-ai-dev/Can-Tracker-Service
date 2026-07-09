# Plan 05: Family And Member CRUD APIs

## Goal

Implement authenticated APIs for creating, reading, updating, searching, filtering, and soft deleting families and members.

## Context

The current HTML supports adding and editing families and members in browser memory. It also searches by family, member, PAN, and CAN. The backend must provide durable storage and API contracts that support the same workflows with proper validation, role access, PII masking, and audit.

## In Scope

- Family database model and migration.
- Member database model and migration.
- CRUD service layer.
- Search and filters.
- Pagination and sorting.
- Soft delete behavior.
- Validation for required fields, enums, PAN, IFSC, dates, amounts, and unique CAN.
- API response contracts for frontend integration.
- Audit integration for all create, update, and delete actions.

## Out Of Scope

- Dashboard counters.
- Computed task endpoints.
- Import endpoints.
- Report export generation.
- Multiple CANs per member.
- Multiple bank accounts per member.

## Design

### Database Tables

`families`:

- `id`
- `family_code`
- `family_head_name`
- `primary_rm_id`
- `remarks`
- `created_at`
- `updated_at`
- `deleted_at`

Constraints and indexes:

- unique active `family_code`.
- index on `primary_rm_id`.
- search index for `family_head_name` and `family_code`.

`members`:

- `id`
- `family_id`
- `name`
- `can_number`
- encrypted and masked PAN fields.
- `date_of_birth`
- `kyc_status`
- encrypted and masked mobile fields.
- `mobile_verification_status`
- encrypted and masked email fields.
- `email_verification_status`
- `nominee_verification_status`
- `bank_name`
- encrypted and masked bank account fields.
- `ifsc_code`
- `payeezz_mandate_status`
- `payeezz_amount`
- `payeezz_start_date`
- `remarks`
- `created_at`
- `updated_at`
- `deleted_at`

Constraints and indexes:

- unique active `can_number`.
- index on `family_id`.
- index on `kyc_status`.
- index on `payeezz_mandate_status`.
- index on `mobile_verification_status`, `email_verification_status`, and `nominee_verification_status`.
- search hash indexes for PAN, mobile, and email.
- search index for member name and CAN.

### Endpoints

Families:

- `GET /api/v1/families`
- `POST /api/v1/families`
- `GET /api/v1/families/{family_id}`
- `PATCH /api/v1/families/{family_id}`
- `DELETE /api/v1/families/{family_id}`
- `GET /api/v1/families/{family_id}/members`
- `POST /api/v1/families/{family_id}/members`

Members:

- `GET /api/v1/members`
- `GET /api/v1/members/{member_id}`
- `PATCH /api/v1/members/{member_id}`
- `DELETE /api/v1/members/{member_id}`
- `GET /api/v1/members/search` as an alias only if the frontend needs a dedicated search path later; default v1 should use `GET /api/v1/members?q=...`.

### Family List Filters

`GET /api/v1/families` supports:

- `q`: family head, family code, member name, CAN, or exact PAN search.
- `rm_id`
- `status_filter`: `all`, `kyc_pending`, `payeezz_pending`, `contact_pending`, `nominee_pending`.
- `limit`
- `offset`
- `sort`: default `family_head_name`.

### Member List Filters

Member list endpoints support:

- `q`
- `family_id`
- `rm_id`
- `kyc_status`
- `payeezz_mandate_status`
- `mobile_verification_status`
- `email_verification_status`
- `nominee_verification_status`
- `limit`
- `offset`

### Validation

Family:

- `family_code` is generated when omitted and remains unique among active families.
- `family_head_name` required.
- `primary_rm_id` required and must reference active user with role `rm`.

Member:

- `family_id` required and active.
- `name` required.
- `can_number` required and unique among active members.
- `kyc_status`, verification statuses, and PayEezz status must use canonical enum labels.
- PAN, if present, must be normalized uppercase and match Indian PAN format.
- IFSC, if present, must be normalized uppercase and match IFSC format.
- PayEezz amount, if present, must be non-negative.
- PayEezz start date can be null unless status is `Approved`; if business later requires it, add a migration-backed validation change.

### Response Contract

Family summary item:

- `id`
- `family_code`
- `family_head_name`
- `primary_rm`
- `total_members`
- `total_cans`
- `last_updated_at`
- `remarks`
- compliance percentages.

Member item:

- `id`
- `family_id`
- `name`
- `can_number`
- `pan_masked`
- `date_of_birth`
- `kyc_status`
- `mobile_masked`
- `mobile_verification_status`
- `email_masked`
- `email_verification_status`
- `nominee_verification_status`
- `bank_name`
- `bank_account_number_masked`
- `ifsc_code`
- `payeezz_mandate_status`
- `payeezz_amount`
- `payeezz_start_date`
- `remarks`
- `updated_at`
- `updated_by`

## Implementation Steps

1. Create family and member SQLAlchemy models.
2. Add migrations with indexes and constraints.
3. Add Pydantic request and response schemas.
4. Add repositories for family/member queries.
5. Add service layer with validation, PII processing, and audit calls.
6. Implement family endpoints.
7. Implement member endpoints.
8. Add search and filter behavior.
9. Add soft delete behavior with audit entries.
10. Add integration tests for all role and validation paths.

## Subagent Usage

- Use parallel `cavecrew-investigator` passes once scaffold exists: one for models/migrations, one for route patterns, one for tests.
- Use the main thread for schema, validation, and service design because this milestone spans many files.
- Use `cavecrew-builder` for small endpoint or serializer fixes only after the main implementation is stable.
- Use `cavecrew-reviewer` to audit for missing role checks, missing audit writes, and response leakage of sensitive fields.

## Test Plan

- Admin and Ops can create and update families.
- Management cannot write families or members.
- RM can access only assigned families.
- Family code uniqueness is enforced.
- CAN uniqueness is enforced.
- PAN and IFSC normalization and validation work.
- Soft-deleted families and members are excluded from default lists.
- Search by family name, family code, member name, CAN, and exact PAN works.
- Status filters return correct family/member sets.
- All writes create audit records.
- Sensitive fields are masked in member responses.

## Acceptance Criteria

- Frontend family and member modals can be backed by these endpoints.
- All CRUD writes are transactional and auditable.
- Lists are paginated.
- Filters match the generated HTML semantics.
- RM visibility is enforced at query level, not just after data is loaded.

## Risks & Mitigations

- Risk: list queries become slow with thousands of CANs. Mitigation: add indexes early and use paginated queries.
- Risk: family filters require joins and computed statuses. Mitigation: implement clear query helpers and test generated SQL behavior.
- Risk: soft delete complicates uniqueness. Mitigation: use partial unique indexes for active records.

## Dependencies

- [01-domain-model-and-business-rules.md](01-domain-model-and-business-rules.md)
- [02-backend-foundation.md](02-backend-foundation.md)
- [03-auth-rbac-and-users.md](03-auth-rbac-and-users.md)
- [04-pii-security-and-audit.md](04-pii-security-and-audit.md)
