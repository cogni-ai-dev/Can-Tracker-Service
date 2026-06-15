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
- `PII_ENCRYPTION_KEY`
- `PII_SEARCH_HASH_KEY`
- `APP_ENV=local`
- `SESSION_COOKIE_SECURE=false`
- `CORS_ORIGINS=http://127.0.0.1:8000,http://localhost:8000`

Run the API on the host:

```bash
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

Compose is production-oriented. It requires `.env` values and does not publish
PostgreSQL to the host. For local Compose, use non-production secrets and set
`APP_ENV=local`, `SESSION_COOKIE_SECURE=false`, and
`DATABASE_URL=postgresql+psycopg://<POSTGRES_USER>:<POSTGRES_PASSWORD>@postgres:5432/<POSTGRES_DB>`.

Start API and PostgreSQL:

```bash
docker compose --env-file .env up --build
```

Compose publishes only the API:

- API: `http://${API_BIND:-127.0.0.1}:${API_PORT:-8000}`
- PostgreSQL: internal Compose network only

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
