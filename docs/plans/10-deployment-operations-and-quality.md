# Plan 10: Deployment, Operations, And Quality

## Goal

Prepare the backend and integrated frontend for reliable operation on a Docker-based cloud VM with backups, environment management, observability, release gates, and disciplined review.

## Context

The selected initial deployment model is Docker on a cloud VM. The application will store sensitive client data and must be usable by operations staff daily. Deployment must include database backup, secure configuration, audit retention, and quality checks.

## In Scope

- Production Docker configuration.
- Environment variable contract.
- Database backups and restore runbook.
- Basic logging and request IDs.
- Error handling and operational health checks.
- Release checklist.
- QA gates.
- Subagent review workflow.
- Minimal deployment documentation.

## Out Of Scope

- Kubernetes.
- Multi-region high availability.
- Managed secret manager integration for v1.
- Advanced APM.
- Automated email alerts unless later requested.

## Design

### Runtime Services

Production Docker Compose services:

- `api`: FastAPI application.
- `postgres`: PostgreSQL database.
- optional `reverse_proxy`: Caddy or Nginx for TLS and static file serving.

Do not expose Postgres publicly. Only API/reverse proxy should be reachable from outside the VM.

### Environment Variables

Required production variables:

- `APP_ENV=production`
- `APP_SECRET_KEY`
- `DATABASE_URL`
- `PII_ENCRYPTION_KEY`
- `PII_SEARCH_HASH_KEY`
- `SESSION_COOKIE_NAME`
- `SESSION_COOKIE_SECURE=true`
- `CORS_ORIGINS`
- `LOG_LEVEL=INFO`
- `BACKUP_RETENTION_DAYS`

Secrets must not be committed. Provide `.env.example` with placeholder values only.

### Health And Observability

Use:

- `GET /health` for process liveness.
- `GET /ready` for database readiness.
- JSON logs in production.
- Request id in every request log.
- Actor id in audit logs, not raw sensitive values.
- Structured error responses without stack traces.

### Backups

Backup policy:

- Daily PostgreSQL logical backup.
- Keep at least 14 days by default.
- Store backups outside the running database container volume.
- Document restore procedure and test it before first production use.

Restore acceptance:

- Restore backup to a clean database.
- Run migrations.
- Verify user login.
- Verify dashboard counters.
- Verify one family detail page.

### Release Gates

Before production release:

- Unit tests pass.
- Integration tests pass.
- Migration applies cleanly on empty database.
- Migration applies cleanly on a copy of staging data.
- Security tests for PII masking pass.
- Role authorization tests pass.
- Import validation tests pass.
- Report export tests pass.
- `cavecrew-reviewer` or equivalent review has no unresolved high or medium findings.

### Operational Runbooks

Create runbooks for:

- Initial deployment.
- Creating first admin user.
- Rotating app secret and PII keys.
- Running database backup.
- Restoring database backup.
- Import failure triage.
- Report export troubleshooting.
- Checking audit trail for a member update.

Key rotation note:

- PII key rotation requires a planned re-encryption process. Do not rotate `PII_ENCRYPTION_KEY` without a migration script that decrypts with old key and re-encrypts with new key.

## Implementation Steps

1. Harden Dockerfile for production.
2. Create production Compose file or Compose profile.
3. Add `.env.example`.
4. Add structured logging and request id middleware.
5. Add backup script and restore documentation.
6. Add deployment README section.
7. Add release checklist.
8. Run full test suite.
9. Run migration smoke tests.
10. Run final review and resolve findings.

## Subagent Usage

- Use `cavecrew-investigator` to inspect deployment files, settings, and test commands before hardening release docs.
- Use the main thread for production security and backup decisions.
- Use `cavecrew-builder` for narrow doc or script edits after exact paths are known.
- Use `cavecrew-reviewer` for final diff review focused on secrets, exposed ports, missing backup steps, and broken commands.
- For broad release readiness, run parallel investigator passes for config, tests, and docs.

## Test Plan

- Docker production build succeeds.
- API starts with production-like environment variables.
- `/health` and `/ready` pass.
- Database migrations apply to empty database.
- Backup command creates a restorable dump.
- Restore procedure works on a clean database.
- Logs contain request id and do not contain sensitive values.
- Production config rejects missing required secrets.
- Release checklist can be completed from a clean checkout.

## Acceptance Criteria

- A new operator can deploy the app to a cloud VM using documented steps.
- Backups are automated or documented with exact commands.
- Restore has been tested at least once.
- Production secrets are not committed.
- Health checks support uptime monitoring.
- Quality gates are explicit and repeatable.

## Risks & Mitigations

- Risk: local-only assumptions break production. Mitigation: test Docker production profile before release.
- Risk: backups exist but restore fails. Mitigation: include restore test in release gates.
- Risk: sensitive values leak through logs. Mitigation: structured redaction and security tests.
- Risk: key rotation is mishandled. Mitigation: document that PII key rotation requires a dedicated re-encryption migration.

## Dependencies

- [02-backend-foundation.md](02-backend-foundation.md)
- [03-auth-rbac-and-users.md](03-auth-rbac-and-users.md)
- [04-pii-security-and-audit.md](04-pii-security-and-audit.md)
- [05-family-member-crud-apis.md](05-family-member-crud-apis.md)
- [06-dashboard-and-computed-tasks.md](06-dashboard-and-computed-tasks.md)
- [07-mfu-import-and-sync.md](07-mfu-import-and-sync.md)
- [08-reporting-and-exports.md](08-reporting-and-exports.md)
- [09-frontend-api-integration.md](09-frontend-api-integration.md)

