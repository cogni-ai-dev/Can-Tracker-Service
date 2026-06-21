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
- `CORS_ORIGINS=http://127.0.0.1:3001,http://localhost:3001`

Run the API on the host:

```bash
export DATABASE_URL=postgresql+psycopg://can:can@127.0.0.1:5402/can
export DATABASE_SCHEMA=can_tracker
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8001
```

The API listens on `http://127.0.0.1:8001`.

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

## React Frontend

The long-term UI lives under `frontend/` as the **MFU Operations Portal**. It
uses React, TypeScript, Vite, Tailwind, React Router, `lucide-react`, and
`recharts`.

Run the API first, then start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Vite serves the app on `http://127.0.0.1:3001` and proxies `/api` to the local
FastAPI backend at `http://127.0.0.1:8001`.

The new React app keeps Compliance wired to the existing backend APIs. Client
CRM uses local/mock adapters in v1 and documents the future `/api/v1/crm/*`
contracts in code. The standalone `can_tracker_dashboard.html` remains as a
legacy transition shell while the React app becomes the primary frontend.

## Docker Compose

Compose is split into PostgreSQL, API, and React frontend stacks. For local
Compose, use non-production secrets and set `APP_ENV=local`,
`SESSION_COOKIE_SECURE=false`,
`DATABASE_URL=postgresql+psycopg://can:can@host.docker.internal:5402/can`,
and `DATABASE_SCHEMA=can_tracker`.

Start PostgreSQL, then the API, then the React frontend:

```bash
docker compose -f docker/can-postgres/docker-compose.yml up -d
docker compose --env-file .env -f docker/can-tracker-service/docker-compose.yml up -d --build
docker compose --env-file .env -f docker/can-tracker-frontend/docker-compose.yml up -d --build
```

The frontend container serves the built React app and proxies `/api` to
`${API_UPSTREAM:-http://host.docker.internal:8001}` so browser requests stay
same-origin.

For the legacy standalone HTML UI only, run:

```bash
uv run python scripts/serve_ui.py
```

Compose publishes:

- API: `http://${API_BIND:-127.0.0.1}:${API_PORT:-8001}`
- React UI: `http://${UI_BIND:-127.0.0.1}:${UI_PORT:-3001}`
- Legacy standalone UI: `http://127.0.0.1:8081`
- PostgreSQL: `127.0.0.1:5402`

The API container runs `alembic upgrade head` before starting Uvicorn.

Production deployment and operations docs:

- [Initial deployment](docs/runbooks/initial-deployment.md)
- [Database backup and restore](docs/runbooks/database-backup-and-restore.md)
- [First admin creation](docs/runbooks/first-admin.md)
- [Release checklist](docs/runbooks/release-checklist.md)

## Health Endpoints

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/ready
curl http://127.0.0.1:8001/api/v1/meta
```
