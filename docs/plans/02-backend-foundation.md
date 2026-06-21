# Plan 02: Backend Foundation

## Goal

Create the FastAPI and PostgreSQL foundation that all later backend features will build on.

## Context

The repository currently has only a README and a standalone HTML file. There is no backend project structure, dependency management, test harness, migration setup, or containerized development environment.

## In Scope

- Python project scaffold.
- FastAPI app factory.
- Settings and environment management.
- SQLAlchemy database setup.
- Alembic migrations.
- Docker Compose for local API and PostgreSQL.
- Health and readiness endpoints.
- Test harness with database fixtures.
- Basic code quality commands.

## Out Of Scope

- Auth implementation.
- Domain tables beyond a minimal migration smoke test.
- PII encryption.
- Business CRUD endpoints.
- Frontend changes.

## Design

### Project Layout

Use this structure:

```text
app/
  __init__.py
  main.py
  api/
    __init__.py
    deps.py
    v1/
      __init__.py
      router.py
  core/
    __init__.py
    config.py
    database.py
    logging.py
    security.py
  domain/
    __init__.py
    enums.py
    calculations.py
  models/
    __init__.py
    base.py
  schemas/
    __init__.py
  services/
    __init__.py
  repositories/
    __init__.py
alembic/
tests/
```

### Dependencies

Use:

- FastAPI
- Uvicorn
- Pydantic settings
- SQLAlchemy 2
- Alembic
- psycopg
- pytest
- pytest-asyncio if async DB access is selected
- httpx
- ruff

Default to synchronous SQLAlchemy unless a clear need for async access appears. This keeps migrations, tests, and service code simpler for v1.

### Settings

Configuration lives in environment variables and is exposed through `app.core.config.Settings`.

Required settings:

- `APP_ENV`
- `APP_SECRET_KEY`
- `DATABASE_URL`
- `PII_ENCRYPTION_KEY`
- `PII_SEARCH_HASH_KEY`
- `SESSION_COOKIE_NAME`
- `SESSION_COOKIE_SECURE`
- `CORS_ORIGINS`
- `LOG_LEVEL`

### API Foundation

Endpoints:

- `GET /health`: process health check, no database dependency.
- `GET /ready`: readiness check that verifies database connectivity.
- `GET /api/v1/meta`: returns API version and environment-safe metadata.

### Database Foundation

Use:

- UUID primary keys.
- `created_at`, `updated_at`, `deleted_at` columns on mutable entities.
- UTC `timestamptz` columns.
- Naming convention for constraints so Alembic migrations are stable.

### Local Development

Docker Compose services:

- `api`
- `postgres`

Expose:

- API on `127.0.0.1:8001`.
- Postgres on a configurable local port.

## Implementation Steps

1. Add Python dependency management files.
2. Create the project layout.
3. Implement settings loading and validation.
4. Implement SQLAlchemy engine, session dependency, and declarative base.
5. Initialize Alembic with the same metadata naming convention used by models.
6. Add health, readiness, and meta routes.
7. Add Dockerfile and Docker Compose.
8. Add pytest configuration and a database fixture strategy.
9. Add README developer commands or link them from the root README.
10. Run tests and a migration smoke check.

## Subagent Usage

- Use `cavecrew-investigator` only if a backend scaffold already exists by the time this plan is implemented.
- Use the main thread for scaffold creation because it touches many files and establishes conventions.
- Use `cavecrew-reviewer` on the final scaffold diff to catch missing settings, broken imports, and migration issues.
- Use `cavecrew-builder` only for narrow follow-up fixes, such as correcting one config default or one route path.

## Test Plan

- `GET /health` returns 200 without database.
- `GET /ready` returns 200 when Postgres is available.
- `GET /ready` returns a controlled failure when database connectivity fails.
- Settings validation fails fast when required secrets are missing outside test mode.
- Alembic can create an initial revision and apply it to an empty database.
- Pytest can create and tear down a test database schema.

## Acceptance Criteria

- `uvicorn app.main:app` starts locally.
- Docker Compose starts API and Postgres.
- Health and readiness endpoints work.
- Tests run through one command.
- Alembic is configured and can apply migrations.
- No business feature code is mixed into the foundation milestone.

## Risks & Mitigations

- Risk: dependency setup blocks future contributors. Mitigation: document exact commands in README and keep Docker Compose working.
- Risk: async DB complexity slows development. Mitigation: default to synchronous SQLAlchemy unless proven necessary.
- Risk: settings differ across local and Docker. Mitigation: load all settings from environment and provide an example env file.

## Dependencies

- [01-domain-model-and-business-rules.md](01-domain-model-and-business-rules.md)
