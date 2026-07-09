# Key Rotation

## App Secret

`APP_SECRET_KEY` signs session token hashes. Rotating it invalidates existing sessions.

Procedure:

```bash
openssl rand -hex 32
vi .env
docker compose -f docker/can-tracker-service/docker-compose.yml up -d can-tracker-service
```

After rotation, all users must log in again.

## PII Keys

Do not rotate `PII_ENCRYPTION_KEY` or `PII_SEARCH_HASH_KEY` by editing `.env` alone.

PII key rotation requires a planned migration that:

1. Starts with the old keys.
2. Decrypts each encrypted value.
3. Re-encrypts with the new encryption key.
4. Recomputes deterministic search hashes with the new hash key.
5. Verifies masked fields and exact search behavior.
6. Takes and tests a backup before and after the migration.

Changing either PII key without that process can make stored client data unreadable or unsearchable.
