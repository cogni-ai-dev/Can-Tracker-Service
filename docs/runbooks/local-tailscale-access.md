# Local Tailscale Access

Use this when you want to run CAN Tracker locally and access it from another device through your Tailscale tailnet.

## Ports

- Backend API: `http://127.0.0.1:8001`
- React frontend: `http://127.0.0.1:3001`
- Backend API over Tailscale IP: `http://100.103.198.93:8001`
- React frontend over Tailscale IP: `http://100.103.198.93:3001`
- Legacy standalone UI proxy: `http://127.0.0.1:8081`
- PostgreSQL: `127.0.0.1:5402`

Do not expose PostgreSQL through Tailscale Serve or Funnel.

## Recommended Docker Setup

Expose services directly on this machine's Tailscale IP using the same visible port numbers as the local services. The frontend still calls same-origin `/api/v1`, and the frontend container proxies `/api` to the backend at `http://100.103.198.93:8001`.

Set the bind addresses in `.env` to this machine's Tailscale IP:

```bash
API_BIND=100.103.198.93
UI_BIND=127.0.0.1
API_UPSTREAM=http://100.103.198.93:8001
CORS_ORIGINS=http://127.0.0.1:3001,http://localhost:3001,http://100.103.198.93:3001
```

Keep the frontend Docker port on localhost and publish it to the tailnet with Tailscale's raw TCP forward:

```bash
tailscale serve --bg --tcp=3001 tcp://127.0.0.1:3001
```

This makes `http://100.103.198.93:3001` work as a normal IP-and-port URL. Keep the backend on `API_BIND=<tailscale-ip>` so the direct API port is published on the Tailscale IP.

Terminal 1:

```bash
docker compose -f docker/can-postgres/docker-compose.yml up -d
docker compose --env-file .env -f docker/can-tracker-service/docker-compose.yml up -d --build
```

Terminal 2:

```bash
docker compose --env-file .env -f docker/can-tracker-frontend/docker-compose.yml up -d --build
```

Open these URLs from another device in your tailnet:

```text
http://100.103.198.93:3001
http://100.103.198.93:8001
```

Use the frontend URL for normal app usage. The backend URL is for direct API checks and diagnostics.

## Vite Dev Alternative

For frontend development with hot reload, run the backend on `8001`, then start Vite:

```bash
cd frontend
npm run dev
```

Vite serves `http://127.0.0.1:3001` and proxies `/api` to `http://127.0.0.1:8001`.

## Serve Vs Funnel

Tailscale Serve is not required for direct Tailscale IP access.

Use Tailscale TCP forwarding when you want raw `http://<tailscale-ip>:<port>` access to a localhost-only service. Use Tailscale HTTPS Serve when you want Tailscale-managed HTTPS hostnames like `https://oxygen.tailc575b5.ts.net:3001`. Use Tailscale Funnel only if you intentionally want public internet access. Funnel has additional requirements and exposes the app outside your tailnet.

## Troubleshooting

If Vite rejects the Tailscale hostname, add that hostname to Vite `server.allowedHosts` in `frontend/vite.config.ts`.

If API requests fail, confirm:

- The backend is running on `127.0.0.1:8001`.
- The frontend is running on `127.0.0.1:3001`.
- Docker publishes backend on `100.103.198.93:8001`.
- Docker publishes frontend on `127.0.0.1:3001`, and Tailscale forwards `100.103.198.93:3001` to it.
- Docker frontend `API_UPSTREAM` is `http://100.103.198.93:8001`, or Vite still proxies `/api` to `http://127.0.0.1:8001`.
- Normal browser app usage starts from `http://100.103.198.93:3001`.
- `tailscale serve status` shows `tcp://100.103.198.93:3001` forwarding to `tcp://127.0.0.1:3001`.
- If the Tailscale IP changes, update `API_BIND`, `API_UPSTREAM`, and the Tailscale CORS origin in `.env`, then recreate the API and frontend containers.
