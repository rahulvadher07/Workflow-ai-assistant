# WorkFlow AI Architecture

## Application layers

The repository keeps the existing separation between React presentation, Django API/domain apps, and the AI execution layer. React pages call focused service modules, while Django apps own authentication, authorization, validation, persistence, and domain workflows.

## Domain applications

- `accounts`: users, profiles, authentication, registration approval, and admin user updates.
- `company`: company configuration, departments, company rules, payroll rules, and Knowledge & Policy documents.
- `attendance`: punch records, attendance days, and attendance services.
- `leave`: leave types, balances, requests, approvals, rejection, and cancellation.
- `teams`: teams and memberships.
- `workspace`: team conversations, messages, tasks, issues, and realtime workspace consumers.
- `notifications`: notification persistence, outbox/tasks, daily brief, and notification WebSockets.
- `payroll`: salaries, payroll periods, payslips, generation, approval, and downloads.
- `ai`: rule catalog, routing, orchestration, tool registry, Knowledge & Policy retrieval, and AI views.
- `core`: shared authentication, permissions, exception handling, realtime support, and WebSocket JWT middleware.

## Request flow

```text
React page/service
      ↓
Django REST endpoint
      ↓
authentication + permission checks
      ↓
serializer/view/service/domain operation
      ↓
Django model/database
```

## Realtime flow

Mutations emit data-change events after successful persistence. Frontend consumers subscribe to the relevant resource and reload only affected state. The persistent data-change WebSocket and notification WebSocket use authenticated ASGI consumers; Redis-backed channels are available for multi-process deployment.

## AI boundary

```text
User message
 → rule catalog / routing
 → scope and intent validation
 → confirmation gate (when required)
 → tool registry
 → deterministic tool
 → backend authorization + business validation
 → result
```

The AI layer does not bypass Django authorization or write to the database directly. `backend/ai/agent_rules.json` remains the declarative policy source.
