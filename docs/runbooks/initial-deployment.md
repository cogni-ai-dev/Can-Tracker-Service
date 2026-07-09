# Initial Deployment

This runbook deploys the UI, API, and PostgreSQL on one cloud VM with Docker Compose.

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
- `API_BIND=0.0.0.0` for direct Compose access on port `8002`; use `127.0.0.1` when a local reverse proxy is the only public entrypoint.
- `UI_BIND=0.0.0.0` for direct Compose access on port `3002`; use `127.0.0.1` when a local reverse proxy is the only public entrypoint.
- `API_UPSTREAM=http://can-tracker-service:8002`

## Deploy

If runtime values are in the root `.env`, run from the repository root:

```bash
docker compose -f docker/can-postgres/docker-compose.yml up -d
docker compose -f docker/can-tracker-service/docker-compose.yml up -d --build
docker compose -f docker/can-tracker-ui/docker-compose.yml up -d --build
```

If runtime values are in local ignored `docker-compose.override.yml` files, run
Compose from each service directory so the override is auto-loaded:

```bash
docker compose -f docker/can-postgres/docker-compose.yml up -d
(cd docker/can-tracker-service && docker compose up -d --build)
(cd docker/can-tracker-ui && docker compose up -d --build)
```

The API container runs `alembic upgrade head` before starting Uvicorn. The API
Compose file creates `can-tracker-local`; the UI Compose file joins that shared
network and proxies `/api` to `can-tracker-service`.

## Verify

```bash
docker compose -f docker/can-postgres/docker-compose.yml ps
docker compose -f docker/can-tracker-service/docker-compose.yml ps
docker compose -f docker/can-tracker-ui/docker-compose.yml ps
docker compose -f docker/can-tracker-service/docker-compose.yml logs --tail=100
docker compose -f docker/can-tracker-ui/docker-compose.yml logs --tail=100
curl -fsS http://127.0.0.1:8002/health
curl -fsS http://127.0.0.1:8002/ready
curl -fsS http://127.0.0.1:8002/api/v1/meta
curl -fsS http://127.0.0.1:3002/health
```

Expected results:

- `postgres` is healthy.
- `can-tracker-service` is healthy.
- `can-tracker-ui` is healthy.
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
