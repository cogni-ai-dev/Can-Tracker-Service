# Database Backup And Restore

Backups are PostgreSQL custom-format logical dumps written to host storage outside the database container volume.

## Run A Backup

```bash
./scripts/backup_postgres.sh
```

Optional overrides:

```bash
BACKUP_DIR=/var/backups/can-tracker BACKUP_RETENTION_DAYS=30 ./scripts/backup_postgres.sh
```

The script prints the dump path and creates a matching `.sha256` file.
By default, dumps are written to `/var/backups/can-tracker`; keep backups outside the repository and outside the Docker database volume.

## Schedule Daily Backups

Example cron entry:

```cron
15 2 * * * cd /opt/can-tracker && BACKUP_DIR=/var/backups/can-tracker ./scripts/backup_postgres.sh >> /var/log/can-tracker-backup.log 2>&1
```

Copy backups to off-VM storage after each successful run.

## Restore To A Clean Database

Stop API writes first:

```bash
BACKUP_FILE=/var/backups/can-tracker/<dump-file>.dump

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum -c "${BACKUP_FILE}.sha256"
else
  shasum -a 256 -c "${BACKUP_FILE}.sha256"
fi
```

Only continue after checksum verification succeeds.

Stop API writes:

```bash
docker compose --env-file .env -f docker/can-tracker-service/docker-compose.yml stop api
```

Create a clean target database and restore the dump:

```bash
docker compose -f docker/can-postgres/docker-compose.yml exec -T postgres sh -c \
  'dropdb --if-exists --username "$POSTGRES_USER" "$POSTGRES_DB" &&
   createdb --username "$POSTGRES_USER" "$POSTGRES_DB"'

docker compose -f docker/can-postgres/docker-compose.yml exec -T postgres sh -c \
  'pg_restore --single-transaction --no-owner --no-privileges --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"' \
  < "$BACKUP_FILE"

docker compose --env-file .env -f docker/can-tracker-service/docker-compose.yml run --rm api alembic upgrade head
docker compose --env-file .env -f docker/can-tracker-service/docker-compose.yml up -d api
```

## Restore Acceptance Checks

```bash
curl -fsS http://127.0.0.1:8001/health
curl -fsS http://127.0.0.1:8001/ready
```

Then verify:

- Admin login succeeds.
- Dashboard counters are plausible.
- One family detail page loads.
- Recent audit log rows are present.
- Report preview for `full` returns rows.

Do not consider a backup policy complete until this restore path has been tested.
