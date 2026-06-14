# Plan 04: PII Security And Audit

## Goal

Protect sensitive client data and maintain a complete field-level audit trail for manual edits, imports, and future MFU API sync.

## Context

The system will store PAN, mobile, email, and bank account details. These values are sensitive and should not be stored or returned as plain text by default. The product requirement also calls for tracking who updated records, when, and with complete audit history.

## In Scope

- PII encryption at rest.
- Masked API responses.
- Deterministic search hashes for exact lookup.
- Field-level audit logs.
- Audit source labels: `manual`, `import`, `mfu_api`.
- Import batch references in audit records.
- Redaction rules for logs and errors.

## Out Of Scope

- External key management service integration for v1.
- Row-level database encryption outside application-managed PII encryption.
- Legal compliance certification.
- User-facing audit UI beyond backend APIs.

## Design

### Sensitive Fields

Encrypt these fields before database persistence:

- `members.pan`
- `members.mobile`
- `members.email`
- `members.bank_account_number`

Store these alongside encrypted values:

- masked display value, for example `ABCDE****F`, `******7890`, or `bank account ending 5678`.
- deterministic HMAC search hash for exact search.

Do not store full sensitive values in audit logs. Audit entries for sensitive fields should store masked old and new values only.

### Encryption

Use application-level authenticated encryption. Required properties:

- Random nonce per encrypted value.
- Authenticated ciphertext.
- Key loaded from `PII_ENCRYPTION_KEY`.
- Decryption only in service layer.

Use `PII_SEARCH_HASH_KEY` for deterministic HMAC hashes. Do not reuse the encryption key for hashes.

### Response Masking

Default API responses return masked sensitive fields:

- `pan_masked`
- `mobile_masked`
- `email_masked`
- `bank_account_number_masked`

Full sensitive fields are only returned when:

- the route explicitly supports `include_sensitive=true`;
- the current role is allowed;
- the access is audit logged as a sensitive read.

V1 default: only `admin` can request full sensitive values.

### Audit Log Fields

`audit_logs` table:

- `id`: UUID.
- `entity_type`: `family`, `member`, `user`, `import_batch`.
- `entity_id`: UUID.
- `action`: `create`, `update`, `delete`, `restore`, `sensitive_read`, `import_commit`.
- `field_name`: nullable for whole-record actions.
- `old_value`: nullable string, masked for sensitive fields.
- `new_value`: nullable string, masked for sensitive fields.
- `actor_user_id`: nullable for system imports.
- `source`: `manual`, `import`, `mfu_api`.
- `import_batch_id`: nullable UUID.
- `request_id`: nullable string.
- `created_at`: UTC timestamp.

### Audit Rules

- Create one audit row per changed field on update.
- Create one summary audit row on create.
- Create one summary audit row on soft delete.
- Do not create audit rows for unchanged fields.
- Import commits must link audit rows to the import batch.
- Sensitive reads should be logged when full sensitive values are returned.
- Audit logging failures must fail the write transaction. A write without audit is not acceptable.

## Implementation Steps

1. Add encryption and masking utilities with tests.
2. Add sensitive value wrapper helpers for service-layer use.
3. Add audit log model and migration.
4. Add an audit service that accepts old object, new object, actor, source, and optional import batch.
5. Add field diff logic that handles enum, date, numeric, nullable, and sensitive fields.
6. Ensure audit writes happen in the same database transaction as the business write.
7. Add log redaction for sensitive field names and values.
8. Add `GET /api/v1/audit` for Admin and optionally Ops read access.
9. Add tests proving encrypted storage and masked audit values.

## Subagent Usage

- Use `cavecrew-investigator` to find every place sensitive fields are serialized before exposing member APIs.
- Use the main thread for encryption, audit, and transaction boundaries.
- Use `cavecrew-reviewer` with focus on data leaks, missing audit writes, and transaction gaps.
- Use `cavecrew-builder` only for narrow serializer or test fixes after the security design is in place.

## Test Plan

- PII values are not stored in plaintext database columns.
- Same PAN creates the same HMAC search hash and different ciphertext.
- Masking works for PAN, mobile, email, and bank account number.
- Default member responses contain masked values only.
- Unauthorized roles cannot request full sensitive values.
- Authorized full sensitive reads create audit entries.
- Member update creates one audit row per changed field.
- Sensitive field update audit stores masked old and new values.
- Import-sourced audit rows link to import batch.
- If audit insert fails, the business update rolls back.

## Acceptance Criteria

- No plaintext PAN, mobile, email, or bank account value is persisted.
- Sensitive values are redacted from logs, validation errors, and audit values.
- Every write path can attach actor, source, and import batch metadata.
- Audit APIs are protected by role checks.
- Tests prove field-level audit behavior for manual and import sources.

## Risks & Mitigations

- Risk: encryption makes search difficult. Mitigation: use deterministic HMAC search hashes for exact search.
- Risk: full sensitive values leak through debug logs. Mitigation: centralize redaction and avoid logging raw request payloads.
- Risk: audit volume grows quickly. Mitigation: index by entity, actor, source, and timestamp; archive later if needed.

## Dependencies

- [01-domain-model-and-business-rules.md](01-domain-model-and-business-rules.md)
- [02-backend-foundation.md](02-backend-foundation.md)
- [03-auth-rbac-and-users.md](03-auth-rbac-and-users.md)

