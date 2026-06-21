# Audit Trail Lookup

Use this when investigating who changed a member, user, family, or import-related record.

## Query Audit Rows

Login as an admin and keep the session cookie:

```bash
curl -c cookies.txt -X POST http://127.0.0.1:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<admin-email>","password":"<admin-password>"}'
```

Query a known entity:

```bash
curl -b cookies.txt \
  "http://127.0.0.1:8001/api/v1/audit?entity_type=member&entity_id=<member-id>&limit=50"
```

For request-level correlation, filter application logs by the returned `request_id`. Sensitive fields in audit rows are masked by design.

## What To Check

- `actor_user_id`: user who made the change, or `null` for system/bootstrap paths.
- `source`: `manual`, `import`, or `mfu_api`.
- `field_name`: changed field for update rows.
- `old_value` and `new_value`: masked for sensitive fields.
- `import_batch_id`: populated for import-sourced changes.
- `request_id`: matches structured application logs.
