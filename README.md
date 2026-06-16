# Can Tracker Service

FastAPI backend for the MFU CAN tracker.

## Local Backend Setup

Install dependencies:

```bash
uv sync
```

Create local environment values:

```bash
cp .env.example .env
```

For local development, replace placeholders and set:

- `APP_SECRET_KEY`
- `DATABASE_URL`
- `DATABASE_SCHEMA=can_tracker`
- `PII_ENCRYPTION_KEY`
- `PII_SEARCH_HASH_KEY`
- `APP_ENV=local`
- `SESSION_COOKIE_SECURE=false`
- `CORS_ORIGINS=http://127.0.0.1:8000,http://localhost:8000`

Run the API on the host:

```bash
export DATABASE_URL=postgresql+psycopg://can:can@127.0.0.1:5402/can
export DATABASE_SCHEMA=can_tracker
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

The API listens on `http://127.0.0.1:8000`.

Create the first local admin after migrations by providing credentials through
environment variables:

```bash
export BOOTSTRAP_ADMIN_NAME="$YOUR_ADMIN_NAME"
export BOOTSTRAP_ADMIN_EMAIL="$YOUR_ADMIN_EMAIL"
export BOOTSTRAP_ADMIN_PASSWORD="$YOUR_ADMIN_PASSWORD"
uv run python -m app.cli.bootstrap_admin
```

The bootstrap command does not define default credentials. If the email already
exists, it leaves the existing user unchanged.

Useful checks:

```bash
uv run pytest
uv run ruff format . --check
uv run ruff check .
```

## Docker Compose

Compose is split into a PostgreSQL stack and an API stack. For local Compose,
use non-production secrets and set `APP_ENV=local`,
`SESSION_COOKIE_SECURE=false`,
`DATABASE_URL=postgresql+psycopg://can:can@host.docker.internal:5402/can`,
and `DATABASE_SCHEMA=can_tracker`.

Start PostgreSQL, then the API:

```bash
docker compose -f docker/can-postgres/docker-compose.yml up -d
docker compose --env-file .env -f docker/can-tracker-service/docker-compose.yml up --build
```

In a second terminal, serve the standalone UI:

```bash
uv run python scripts/serve_ui.py
```

Compose publishes:

- API: `http://${API_BIND:-127.0.0.1}:${API_PORT:-8000}`
- UI: `http://127.0.0.1:8081`
- PostgreSQL: `127.0.0.1:5402`

The API container runs `alembic upgrade head` before starting Uvicorn.

Production deployment and operations docs:

- [Initial deployment](docs/runbooks/initial-deployment.md)
- [Database backup and restore](docs/runbooks/database-backup-and-restore.md)
- [First admin creation](docs/runbooks/first-admin.md)
- [Release checklist](docs/runbooks/release-checklist.md)

## Health Endpoints

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
curl http://127.0.0.1:8000/api/v1/meta
```
