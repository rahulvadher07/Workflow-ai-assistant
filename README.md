# WorkFlow AI

WorkFlow AI is a full-stack employee operations platform built with React and Django. It combines role-based company workflows with an AI assistant that routes requests through declarative rules, confirmation gates, deterministic tools, backend authorization, and company Knowledge & Policy retrieval.

## Key Features

- JWT authentication with employee registration and HOD approval workflows.
- Role-based portals for Employee, HOD, and Super Admin users.
- Attendance with punch in/out, daily status, history, and working-hours reporting.
- Leave workflows, balances, approvals, rejection/cancellation, and team reporting.
- Team Workspace with conversations, tasks, issues, status updates, and realtime messaging.
- Payroll and payslip generation/approval/download flows.
- In-app notifications with read/unread state and realtime updates.
- Super Admin management for employees, HODs, departments, company rules, Knowledge & Policy documents, and HOD leave approvals.
- AI assistant with rule-driven routing, scoped tool calling, confirmation for protected actions, deterministic reporting, and backend validation.
- Knowledge & Policy retrieval from uploaded PDF documents with lexical ranking and optional semantic embeddings.
- Event-driven realtime data invalidation and authenticated WebSocket channels.

## Technology Stack

**Frontend**: React 19, Vite 8, React Router, Axios, Tailwind CSS, Lucide React.

**Backend**: Python, Django 5.1, Django REST Framework, SimpleJWT, Channels/Daphne, Celery, Redis, PostgreSQL (deployment target), SQLite (local default), Groq, pypdf, ReportLab, and optional sentence-transformers semantic retrieval.

## Architecture

```text
React UI
   │
   ├── Axios services + JWT
   └── WebSocket clients
            │
            ▼
     Django REST / ASGI
            │
      ┌─────┴───────────────┐
      ▼                     ▼
Domain apps            AI orchestration
(accounts/company/     │
 attendance/leave/     ├── rule matching
 teams/workspace/      ├── scope + validation
 notifications/        ├── confirmation gate
 payroll)              ├── tool registry
      │                 └── deterministic tools
      └──────────┬──────────────┘
                 ▼
             Django models
                 │
          SQLite / PostgreSQL
```

For AI requests, the implemented flow is:

```text
User message
 → rule matching / catalog
 → scope + intent validation
 → confirmation when required
 → exact registered tool
 → Django authorization/business validation
 → database/service operation
 → result
 → assistant response
```

The declarative `backend/ai/agent_rules.json` catalog is the routing-policy source of truth, while Python owns execution mechanics and backend tools remain authoritative.

## Roles

### Employee

Employees can access their dashboard, attendance, leave-related workflows, Team Workspace, notifications, payroll/payslips, profile management, and the AI assistant within their permitted scope.

### HOD

HODs can manage their team workspace, review scoped employee registrations, access department/team attendance and leave information, perform permitted approvals, manage team activity, send authorized notifications, and use the AI assistant within department/team scope.

### Super Admin

Super Admins have company-wide administrative access for employees, HODs, departments, company rules, Knowledge & Policy documents, HOD leave approvals, notifications, payroll operations, and administrative workflows.

## Project Structure

```text
WorkFlow-AI/
├── Frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── context/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── routes/
│   │   ├── services/
│   │   └── utils/
│   ├── public/
│   ├── tests/
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.js
├── backend/
│   ├── accounts/
│   ├── ai/
│   ├── attendance/
│   ├── company/
│   ├── core/
│   ├── leave/
│   ├── notifications/
│   ├── payroll/
│   ├── teams/
│   ├── workspace/
│   ├── config/
│   ├── manage.py
│   └── requirements*.txt
├── docs/
├── docker-compose.yml
├── README.md
├── .gitignore
└── .env.example
```

## Local Development Setup

### Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate
pip install -r requirements.txt
# Optional semantic retrieval support
pip install -r requirements-semantic.txt
# From backend/, copy the repository-level example to the file read by Django.
# Windows PowerShell: Copy-Item ..\.env.example .env
# macOS/Linux: cp ../.env.example .env
python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd Frontend
npm install
npm run dev
```

The Vite frontend uses `VITE_API_BASE_URL` and `VITE_WS_BASE_URL`. Their local defaults point to Django on port 8000.

## Environment Variables

`.env.example` documents the configuration names used by the backend, deployment stack, and frontend. Never commit real credentials, API keys, database passwords, or local `.env` files.

For production-style Docker deployment, use `.env.production.example` as the deployment-oriented example.

## AI Assistant

The AI subsystem is centered in `backend/ai/`. `agent_rules.json` defines declarative routing policy. The rule engine validates the catalog, the orchestrator resolves and executes permitted actions, and the tool registry connects action names to deterministic Django-backed implementations.

Protected actions use a centralized confirmation policy. A confirmation is accepted only when there is a live pending preview for the same authenticated user and immediately preceding turn; the frozen tool name and arguments are then executed.

## Knowledge & Policy

Policy documents are uploaded through the company Knowledge & Policy flow and represented by `PolicyDocument` plus indexed `KnowledgeChunk` records. Retrieval uses compact evidence snippets. When semantic retrieval is enabled and the configured sentence-transformers model is available, the system uses hybrid semantic/lexical ranking; otherwise it falls back to lexical ranking.

After enabling semantic retrieval for documents uploaded earlier, refresh their chunks with:

```bash
cd backend
python manage.py reindex_knowledge
```

The repository does not include runtime `media/` or local database contents; upload your own policy PDFs after setup.

## Realtime Notifications

The backend runs through ASGI/Daphne and Channels. The frontend uses authenticated WebSocket connections for notification/data-change events and event-driven resource invalidation. Redis can be enabled for the channel layer and Celery broker in multi-process deployments.

## Testing and Verification

### Frontend

```bash
cd Frontend
npm test
npm run lint
npm run build
```

### Backend

```bash
cd backend
python -m compileall -q .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Management commands also include:

```bash
python manage.py ai_healthcheck
python manage.py reindex_knowledge
```

## Deployment

A Docker Compose deployment is included with PostgreSQL, Redis, Django/Daphne, Celery worker/beat, and an Nginx-served React frontend. See `PRODUCTION_DEPLOYMENT.md` for the existing deployment procedure and required production environment values.

The frontend directory is named `Frontend` in this repository; the compose configuration uses that exact path.

## Security Notes

- Keep real secrets outside source control.
- Use a strong `SECRET_KEY` and real database credentials in deployment environments.
- Configure production `ALLOWED_HOSTS`, CORS/CSRF origins, and HTTPS-related Django security settings appropriately.
- Keep JWT access/refresh tokens and provider credentials out of logs and commits.
- Runtime database, uploaded media, static build output, virtual environments, and caches are intentionally excluded from Git.

## Limitations

The repository contains deployment support, but production security and infrastructure values still need to be supplied and validated for the target environment. Semantic Knowledge & Policy retrieval also depends on the optional sentence-transformers installation and model availability.

## Future Improvements

- Expand automated end-to-end coverage around authentication, AI confirmation, and realtime flows.
- Add CI for frontend build/lint/tests and Django checks/tests on every change.
- Add environment-specific operational monitoring for deployed infrastructure.
