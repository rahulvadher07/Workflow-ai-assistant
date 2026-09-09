# WorkFlow AI production deployment

The included `docker-compose.yml` provides a production-style stack:

- PostgreSQL for the application database
- Redis for Channels and Celery
- Daphne for Django/ASGI HTTP + WebSocket traffic
- Celery worker for asynchronous jobs
- Celery Beat for scheduled jobs
- Nginx-served React frontend with `/api/` and `/ws/` reverse proxies
- Persistent Docker volumes for PostgreSQL, Django static files, and uploaded media

## Start

1. Copy `.env.production.example` to `.env` and set real secrets/domain values.
2. Run `docker compose up -d --build`.
3. For semantic Knowledge & Policy retrieval, keep `AI_SEMANTIC_RETRIEVAL_ENABLED=True`.
4. Existing policy PDFs uploaded before semantic retrieval was enabled can be refreshed with:

```bash
python manage.py reindex_knowledge
```

The backend container automatically runs migrations and `collectstatic` before Daphne starts. Celery worker/beat wait for the backend healthcheck plus database/Redis readiness.

For HTTPS in a real deployment, terminate TLS at an external load balancer/reverse proxy and set the corresponding Django security environment variables.
