# First Admin Creation

The bootstrap command creates the first active `admin` user and writes an audit row. It never uses default credentials.

## Create Admin

Set credentials in the shell running the one-time command:

```bash
export BOOTSTRAP_ADMIN_NAME="<admin-name>"
export BOOTSTRAP_ADMIN_EMAIL="<admin-email>"
export BOOTSTRAP_ADMIN_PASSWORD="<temporary-password>"
```

```bash
docker compose --env-file .env -f docker/can-tracker-service/docker-compose.yml run --rm \
  -e BOOTSTRAP_ADMIN_NAME \
  -e BOOTSTRAP_ADMIN_EMAIL \
  -e BOOTSTRAP_ADMIN_PASSWORD \
  api python -m app.cli.bootstrap_admin
```

The password must be at least eight characters. Use a long random temporary password and rotate it after first login when a user-management flow is available.

## Verify

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<admin-email>","password":"<temporary-password>"}'
```

Expected result: HTTP `200`, a session cookie, and a response user with `"role":"admin"`.

If the email already exists, the command exits successfully and leaves the existing user unchanged.
