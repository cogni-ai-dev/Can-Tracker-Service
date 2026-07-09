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

The React app keeps Compliance wired to the existing backend APIs. Client CRM
uses local/mock adapters in v1 and documents the future `/api/v1/crm/*`
contracts in code. The old standalone `can_tracker_dashboard.html` is no longer
part of the tracked frontend; local copies are ignored by git.

## Docker Compose

Use the tracked separate Compose files for fresh servers and normal local
deploys. PostgreSQL, the API, and the React UI stay in separate Compose files;
the API Compose file creates the shared `can-tracker-local` network, and the UI
Compose file joins that network so it can proxy to
`http://can-tracker-service:8002` without a local override file.

Provide runtime values with either a root `.env` file or local ignored override
files.

If you use `.env`, run from the repository root:

```bash
cp .env.example .env
docker compose -f docker/can-postgres/docker-compose.yml up -d
docker compose -f docker/can-tracker-service/docker-compose.yml up -d --build
docker compose -f docker/can-tracker-ui/docker-compose.yml up -d --build
```

If you put secrets in `docker-compose.override.yml`, run Compose from each
service directory so the override file is auto-loaded:

```bash
docker compose -f docker/can-postgres/docker-compose.yml up -d
(cd docker/can-tracker-service && docker compose up -d --build)
(cd docker/can-tracker-ui && docker compose up -d --build)
```

For logs and status:

```bash
docker compose -f docker/can-postgres/docker-compose.yml ps
docker compose -f docker/can-tracker-service/docker-compose.yml ps
docker compose -f docker/can-tracker-ui/docker-compose.yml ps
docker compose -f docker/can-tracker-service/docker-compose.yml logs --tail=100
docker compose -f docker/can-tracker-ui/docker-compose.yml logs --tail=100
```

The frontend container serves the built React app and proxies `/api` to
`${API_UPSTREAM:-http://can-tracker-service:8002}` so browser requests stay
same-origin.

If you keep a local copy of the old standalone HTML UI, you can serve it with:

```bash
uv run python scripts/serve_ui.py
```

Compose publishes:

- API default: `0.0.0.0:8002` in Docker, reachable locally at `http://127.0.0.1:8002`
- React UI default: `0.0.0.0:3002` in Docker, reachable locally at `http://127.0.0.1:3002`
- Optional local standalone UI: `http://127.0.0.1:8081`
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
