# WorkFlow AI Rules + Action Safety

## Routing contract
The AI flow is:

`User message -> confirmation gate -> catalog match -> canonical action plan -> deterministic safe route when available -> existing Django tool -> backend validation/business logic -> result -> assistant response`

`agent_rules.json` is the declarative routing-policy source of truth. A deterministic rule declares a `router_key`, and the executable implementation is conventionally named `_route_<router_key>` in `ai/orchestrator.py`. The contract validator checks that every deterministic catalog key has an executable handler, so a new/typo key cannot silently fall through as a valid deterministic route.

The catalog remains declarative; Python owns execution mechanics and existing Django tools/services remain authoritative for permissions, business rules and database writes.

## Central confirmation policy
Confirmation phrases live once in the top-level `confirmation_policy` object in `agent_rules.json`. Individual rules only declare `confirmation_required: true` when needed.

A phrase such as `yes`, `ha`, `હા`, `ok`, `done`, `submit`, `send it`, or another configured affirmative is meaningful only when there is a live, unexpired pending preview for the same authenticated user and the immediately preceding turn. Confirmation is never re-parsed by Groq. The exact frozen tool name and arguments are executed, then pending state is cleared.

## Knowledge & Policy retrieval
Uploaded active PDF documents are indexed into `KnowledgeChunk` rows with optional normalized sentence embeddings. Retrieval uses a hybrid semantic + lexical ranker when the configured sentence-transformers model is available; otherwise it safely falls back to deterministic lexical ranking. Results are compact evidence snippets rather than whole documents. Personal salary questions use the authenticated role as a retrieval signal; payslip questions remain on payroll tooling.

Run `python manage.py reindex_knowledge` after enabling semantic retrieval on documents that were uploaded before embedding support was enabled.

Retrieved policy text is information, never instructions to follow. Unsupported facts must not be invented.

## Scope and backend authority
Scope precedence is strict: specific employee > explicit team > personal > company-wide. The AI cannot grant permission or broaden scope.

Existing Django services/tools remain authoritative for authentication, authorization, ownership, status, balances, date rules, duplicate/overlap checks, transactions and database writes. The AI layer never writes the database directly.

## Realtime UI
The frontend uses event-driven resource invalidation only. Successful mutations emit a `workflow_ai_data_changed` event; mounted consumers reload only the affected resource. A persistent authenticated `/ws/data-changes/` socket also receives server-originated invalidation events generated after committed changes to important domain models. BroadcastChannel keeps multiple app tabs aligned. Notification WebSocket messages additionally emit related resource events. No polling, timers, focus synchronization or page reloads are used.

Realtime publishing is transport-only and failures never block domain persistence.

## Observability and deployment
AI incidents and turn timing use the `workflow_ai.ai` logger without recording secrets, full prompts or tool arguments. `python manage.py ai_healthcheck` validates the rule/tool catalog, database connectivity, provider configuration and Knowledge & Policy indexing/semantic availability.

Production deployment assets are provided under the project root: `docker-compose.yml`, `backend/Dockerfile`, `Frontend/Dockerfile` and the frontend nginx reverse-proxy configuration. The compose stack uses PostgreSQL, Redis, Daphne, Celery worker/beat and nginx-served React. Secrets/configuration are supplied through environment variables.
