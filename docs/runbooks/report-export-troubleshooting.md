# Report Export Troubleshooting

Use this when report previews look wrong, an export fails, or a downloaded CSV,
XLSX, or PDF is not usable. Do not paste session cookies or exported sensitive data
into tickets or chat.

## Setup

```sh
export BASE_URL="https://can-tracker.example.com"
export REPORT_TYPE="full"
```

Valid report types are `kyc_pending`, `payeezz_pending`, `contact_pending`,
`family_compliance`, `rm_tasks`, and `full`.

Login with an Admin, Ops, Management, or RM user:

```sh
curl -sS -c cookies.txt -X POST "${BASE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"<user-email>","password":"<password>"}'
```

## Preview Checks

Preview the first page:

```sh
curl -sS "${BASE_URL}/api/v1/reports/${REPORT_TYPE}/preview?limit=10&offset=0" \
  -b cookies.txt
```

Preview with filters:

```sh
curl -sS "${BASE_URL}/api/v1/reports/${REPORT_TYPE}/preview?rm_id=<rm-uuid>&family_id=<family-uuid>&limit=10&offset=0" \
  -b cookies.txt
```

Compare `total`, `columns`, `items`, and `filters` with the user report request.
Admin, Ops, and Management can view all report scopes; RM users see only assigned
family data.

## Export Checks

CSV:

```sh
curl -sS -D /tmp/can-tracker-report.headers -o /tmp/can-tracker-report.csv \
  "${BASE_URL}/api/v1/reports/${REPORT_TYPE}/export?format=csv" \
  -b cookies.txt
```

XLSX:

```sh
curl -sS -D /tmp/can-tracker-report.headers -o /tmp/can-tracker-report.xlsx \
  "${BASE_URL}/api/v1/reports/${REPORT_TYPE}/export?format=xlsx" \
  -b cookies.txt
```

PDF:

```sh
curl -sS -D /tmp/can-tracker-report.headers -o /tmp/can-tracker-report.pdf \
  "${BASE_URL}/api/v1/reports/${REPORT_TYPE}/export?format=pdf" \
  -b cookies.txt
```

Check export headers:

```sh
grep -i "content-type\|content-disposition\|x-report-row-count" /tmp/can-tracker-report.headers
```

`X-Report-Row-Count` should match the preview `total` when the same report type
and filters are used at the same point in time.

## Common Causes

- `invalid_report_type`: use one of the valid report types listed above.
- `invalid_report_format`: use `csv`, `xlsx`, or `pdf`.
- Empty preview or export: confirm the user's role scope, `rm_id`, `family_id`,
  and that matching active family/member/task data exists.
- Row count mismatch: rerun preview and export with identical filters; data may
  have changed between calls.
- PDF missing rows or hard to read: use CSV or XLSX for wide or large reports.
- Unmasked PAN or account data: stop sharing the export and escalate immediately.

## Escalate With

- Report type, format, filters, response status, and request id if available.
- The response headers, including `Content-Type`, `Content-Disposition`, and
  `X-Report-Row-Count`.
- A sanitized description of missing or unexpected rows. Do not attach raw exports
  unless the incident process explicitly allows it.
