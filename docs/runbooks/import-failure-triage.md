# Import Failure Triage

Use this when an MFU template upload validates with errors, conflicts, or an import
commit fails. Do not paste session cookies, PANs, account numbers, or full row payloads
into tickets or chat.

## Setup

```sh
export BASE_URL="https://can-tracker.example.com"
export BATCH_ID="<import-batch-id>"
```

Imports require an Admin or Ops session.

```sh
curl -sS -c cookies.txt -X POST "${BASE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"<admin-or-ops-email>","password":"<password>"}'
```

## Fast Checks

List recent batches:

```sh
curl -sS "${BASE_URL}/api/v1/imports?limit=20&offset=0" \
  -b cookies.txt
```

Filter by status:

```sh
curl -sS "${BASE_URL}/api/v1/imports?status=failed&limit=20&offset=0" \
  -b cookies.txt
```

Inspect one batch:

```sh
curl -sS "${BASE_URL}/api/v1/imports/${BATCH_ID}" \
  -b cookies.txt
```

Inspect row failures:

```sh
curl -sS "${BASE_URL}/api/v1/imports/${BATCH_ID}/rows?status=error&limit=100&offset=0" \
  -b cookies.txt
```

Inspect row conflicts:

```sh
curl -sS "${BASE_URL}/api/v1/imports/${BATCH_ID}/rows?status=conflict&limit=100&offset=0" \
  -b cookies.txt
```

Confirm commit candidates:

```sh
curl -sS "${BASE_URL}/api/v1/imports/${BATCH_ID}/rows?status=valid&limit=100&offset=0" \
  -b cookies.txt
```

Commit only after errors and conflicts are understood. This mutates family/member
records and writes import audit history.

```sh
curl -sS -X POST "${BASE_URL}/api/v1/imports/${BATCH_ID}/commit" \
  -b cookies.txt
```

## Status Guide

- `failed`: batch-level parse, file, or required-header issue. Check batch `errors`
  and `warnings`; re-upload a corrected template.
- `validated`: upload parsed and row validation completed. Review `error_row_count`
  and `conflict_row_count` before commit.
- `committed`: commit already ran. Do not retry by re-uploading unless Operations
  intentionally wants a new import batch.
- `error` rows: bad template data such as missing required values, invalid enum
  labels, invalid PAN/IFSC/date/amount, inactive RM match, or duplicate CAN inside
  the file.
- `conflict` rows: existing CAN belongs to a different family. Resolve ownership
  before another import; conflicted rows do not mutate records.

## Template Checks

- Required headers must be present exactly as documented in
  `docs/plans/07-mfu-import-and-sync.md`.
- Dates must use `YYYY-MM-DD`.
- Enum labels must match canonical labels after trimming whitespace, for example
  `Validated`, `Registered`, `No KYC`, `Verified`, `Not Verified`,
  `Not Available`, `Sent for Approval`, and `Aggregator Accepted`.
- `PrimaryRMEmail` must match one active RM. If only `PrimaryRMName` is present,
  it must match exactly one active RM.
- A CAN number can appear only once in the uploaded file.

## Escalate With

- Batch id, file name, status, row counts, and request id if available.
- Sanitized examples of `errors` values and row numbers only.
- Whether the failure happened during upload validation or `POST /api/v1/imports/{batch_id}/commit`.
