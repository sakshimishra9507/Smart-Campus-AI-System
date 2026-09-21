# Production Deployment

## 1. Local development
Copy .env.example to .env, configure a development secret, then run python manage.py runserver. Never commit env files.

## 2. Environment variables
Required: SECRET_KEY, DEBUG, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, DB_*, POSTGRES_*, REDIS_URL, SANDBOX_IMAGE, LOG_LEVEL. Production secrets belong in a secret manager or CI/CD environment secrets.

## 3. Database setup
Production uses PostgreSQL 16. Configure POSTGRES_* and matching Django DB_* values.

## 4. Migration commands
docker compose -f docker-compose.production.yml run --rm api python manage.py migrate --noinput

## 5. Production build
docker compose -f docker-compose.production.yml build

## 6. Deployment
Create .env.production from .env.production.example with your secret manager, then docker compose -f docker-compose.production.yml up -d. Check /healthz/ and /readyz/.

## 7. Rollback
Redeploy the previous known-good image/version. For schema rollback, use a tested forward migration strategy; do not delete production data.

## 8. Logs
docker compose -f docker-compose.production.yml logs -f api
docker compose -f docker-compose.production.yml logs -f worker

## 9. Troubleshooting
503 ready: inspect PostgreSQL/Redis and environment variables.
400 host/CSRF: verify ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS.
Sandbox unavailable: verify Docker daemon/image/permissions; repository execution must fail closed.
Migration errors: inspect showmigrations and the failing migration.
Never print secrets into logs or issue reports.
