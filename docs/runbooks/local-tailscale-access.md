# Local Tailscale Access

Use this when you want to run CAN Tracker locally and access it from another device through your Tailscale tailnet.

## Ports

- Backend API: `http://127.0.0.1:8000`
- React frontend: `http://127.0.0.1:5173`
- Legacy standalone UI proxy: `http://127.0.0.1:8081`
- PostgreSQL: `127.0.0.1:5402`

Do not expose PostgreSQL through Tailscale Serve or Funnel.

## Recommended Setup

Expose only the React frontend with Tailscale Serve. The frontend calls same-origin `/api/v1`, and Vite proxies `/api` to the local backend at `http://127.0.0.1:8000`.

Terminal 1:

```bash
uv run uvicorn app.main:app --reload
```

Terminal 2:

```bash
cd frontend
npm run dev
```

Terminal 3:

```bash
tailscale serve 5173
```

Open the HTTPS URL printed by Tailscale, usually in this form:

```text
https://your-machine.your-tailnet.ts.net
```

## Serve Vs Funnel

Use Tailscale Serve for private access from devices in your tailnet.

Use Tailscale Funnel only if you intentionally want public internet access. Funnel has additional requirements and exposes the app outside your tailnet.

## Troubleshooting

If Vite rejects the Tailscale hostname, add that hostname to Vite `server.allowedHosts` in `frontend/vite.config.ts`.

If API requests fail, confirm:

- The backend is running on `127.0.0.1:8000`.
- The frontend is running on `127.0.0.1:5173`.
- `frontend/vite.config.ts` still proxies `/api` to `http://127.0.0.1:8000`.
- The browser is opened through the Tailscale Serve HTTPS URL, not the raw backend URL.
