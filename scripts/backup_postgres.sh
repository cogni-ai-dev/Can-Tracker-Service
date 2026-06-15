#!/usr/bin/env sh
set -eu
umask 077

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

ENV_FILE=${ENV_FILE:-"$PROJECT_DIR/.env"}
COMPOSE_FILE=${COMPOSE_FILE:-"$PROJECT_DIR/docker/can-postgres/docker-compose.yml"}
BACKUP_DIR=${BACKUP_DIR:-"/var/backups/can-tracker"}
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-14}
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
BACKUP_FILE="$BACKUP_DIR/can-tracker-$TIMESTAMP.dump"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

cd "$PROJECT_DIR"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T postgres sh -c \
  'pg_dump --format=custom --no-owner --no-privileges --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"' \
  > "$BACKUP_FILE"

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$BACKUP_FILE" > "$BACKUP_FILE.sha256"
else
  shasum -a 256 "$BACKUP_FILE" > "$BACKUP_FILE.sha256"
fi

find "$BACKUP_DIR" -type f \( -name "can-tracker-*.dump" -o -name "can-tracker-*.dump.sha256" \) \
  -mtime +"$RETENTION_DAYS" -print -delete

echo "$BACKUP_FILE"
