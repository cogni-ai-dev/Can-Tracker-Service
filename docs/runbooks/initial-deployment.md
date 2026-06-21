# Initial Deployment

This runbook deploys the API and PostgreSQL on one cloud VM with Docker Compose.

## Prerequisites

- VM firewall allows only SSH, TLS through the reverse proxy, and any explicitly approved management ports.
- Docker Engine with Compose v2 is installed.
- A DNS name points at the VM.
- TLS is terminated by a reverse proxy such as Caddy or Nginx, or by a cloud load balancer.
- Backups are written to host storage outside the Docker volume and copied to off-VM storage.

## Configure Environment

```bash
cp .env.example .env
chmod 600 .env
```

Replace every placeholder in `.env`. Generate independent secrets for:

```bash
openssl rand -hex 32
```

Production values must satisfy:

- `APP_ENV=production`
- `SESSION_COOKIE_SECURE=true`
- `DATABASE_URL=postgresql+psycopg://can:can@host.docker.internal:5402/can`
- `DATABASE_SCHEMA=can_tracker`
- `CORS_ORIGINS=https://<production-domain>`
- `BACKUP_RETENTION_DAYS` is at least `14`
- `API_BIND=0.0.0.0` for direct Compose access on port `8001`; use `127.0.0.1` when a local reverse proxy is the only public entrypoint.

## Deploy

```bash
docker compose -f docker/can-postgres/docker-compose.yml up -d
docker compose --env-file .env -f docker/can-tracker-service/docker-compose.yml build api
docker compose --env-file .env -f docker/can-tracker-service/docker-compose.yml up -d api
```

The API container runs `alembic upgrade head` before starting Uvicorn.

## Verify

```bash
docker compose -f docker/can-postgres/docker-compose.yml ps
docker compose --env-file .env -f docker/can-tracker-service/docker-compose.yml ps
docker compose --env-file .env -f docker/can-tracker-service/docker-compose.yml logs --tail=100 api
curl -fsS http://127.0.0.1:8001/health
curl -fsS http://127.0.0.1:8001/ready
curl -fsS http://127.0.0.1:8001/api/v1/meta
```

Expected results:

- `postgres` is healthy.
- `api` is healthy.
- `/health` returns `{"status":"ok"}`.
- `/ready` returns `{"status":"ready"}`.
- API logs are JSON in production and include `request_id`.

## Initial Data

Create the first admin with [first-admin.md](first-admin.md), then verify login through the frontend or `POST /api/v1/auth/login`.

## Operational Checks

Before handing the service to operations:

- Run one backup with [database-backup-and-restore.md](database-backup-and-restore.md).
- Restore that backup to a clean database at least once.
- Verify login, dashboard counters, and one family detail page after restore.
- Confirm Postgres host port `5402` is not exposed beyond approved hosts and firewall rules.
- Confirm `.env` is not committed.
