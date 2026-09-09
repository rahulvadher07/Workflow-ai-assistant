# Development Guide

## Backend

From `backend/`, create a virtual environment and install `requirements.txt`. Install `requirements-semantic.txt` when semantic Knowledge & Policy retrieval is needed. Configure values from the root `.env.example`, then run migrations and `python manage.py runserver`.

## Frontend

From `Frontend/`, run `npm install` and `npm run dev`. The project uses npm scripts defined in `package.json`; the committed `package-lock.json` is the dependency lockfile used by Docker with `npm ci`.

## Useful checks

```bash
# frontend
npm test
npm run lint
npm run build

# backend
python -m compileall -q .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py ai_healthcheck
```

Do not delete or rewrite migrations as part of routine cleanup. Treat them as historical records.
