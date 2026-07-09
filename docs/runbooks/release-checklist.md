# Release Checklist

Complete this checklist before deploying to production.

## Code And Tests

- [ ] `uv run ruff format . --check`
- [ ] `uv run ruff check .`
- [ ] `uv run pytest`
- [ ] Migration applies to an empty database.
- [ ] Migration applies to a copy of staging or production-like data.
- [ ] Docker production build succeeds: `docker compose -f docker/can-tracker-service/docker-compose.yml build can-tracker-service && docker compose -f docker/can-tracker-ui/docker-compose.yml build can-tracker-ui`.

## Security Gates

- [ ] `.env` is not committed.
- [ ] `.env.example` contains placeholders only.
- [ ] `APP_ENV=production`.
- [ ] `SESSION_COOKIE_SECURE=true`.
- [ ] `APP_SECRET_KEY`, `PII_ENCRYPTION_KEY`, and `PII_SEARCH_HASH_KEY` are independent strong values.
- [ ] Postgres host port `5402` is protected by firewall rules or replaced with a private database endpoint.
- [ ] API is behind TLS through a reverse proxy or approved load balancer.
- [ ] PII masking tests pass.
- [ ] Role authorization tests pass.
- [ ] Logs contain request IDs and do not contain raw PAN, email, mobile, or bank account values.

## Functional Gates

- [ ] First admin creation is tested.
- [ ] Login/logout/current-user flow is tested.
- [ ] Family/member CRUD is tested.
- [ ] Dashboard and computed tasks are tested.
- [ ] MFU import upload, validation, conflict preview, and commit are tested.
- [ ] CSV, XLSX, and PDF report export tests pass.
- [ ] Frontend API integration checks pass.

## Operations Gates

- [ ] Backup script creates a custom-format dump and checksum.
- [ ] Restore procedure has been tested on a clean database.
- [ ] Restore verification covers login, dashboard counters, and one family detail page.
- [ ] Backup retention is at least 14 days.
- [ ] Off-VM backup copy is configured.
- [ ] Initial deployment runbook has been followed end to end.
- [ ] Import failure and report export troubleshooting runbooks are reviewed by operations.

## Review Gate

- [ ] Final diff review has no unresolved high or medium findings for secrets, exposed ports, backup/restore gaps, or broken commands.
