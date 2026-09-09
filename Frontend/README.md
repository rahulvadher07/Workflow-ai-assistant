# WorkFlow AI Frontend

React + Vite frontend for the WorkFlow AI employee operations platform.

## Development

```bash
npm install
npm run dev
```

## Available scripts

```bash
npm run dev
npm run build
npm run lint
npm test
```

## Environment

Create `Frontend/.env` from `Frontend/.env.example` and set:

- `VITE_API_BASE_URL` — Django REST API base URL
- `VITE_WS_BASE_URL` — WebSocket base URL

The frontend uses Axios for REST calls, BrowserRouter for application routing, React contexts for authentication/notifications/realtime state, and focused service modules for backend APIs.
