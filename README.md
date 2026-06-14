# Can Tracker Service

FastAPI backend foundation for the MFU CAN tracker.

## Local Backend Setup

Install dependencies:

```bash
uv sync
```

Create local environment values:

```bash
cp .env.example .env
```

For local development, provide real non-production values for:

- `APP_SECRET_KEY`
- `DATABASE_URL`
- `PII_ENCRYPTION_KEY`
- `PII_SEARCH_HASH_KEY`

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

Start API and PostgreSQL:

```bash
docker compose up --build
```

Compose exposes:

- API: `http://127.0.0.1:8000`
- PostgreSQL: `127.0.0.1:${POSTGRES_PORT:-5432}`

The API container runs `alembic upgrade head` before starting Uvicorn.

## Health Endpoints

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
curl http://127.0.0.1:8000/api/v1/meta
```
