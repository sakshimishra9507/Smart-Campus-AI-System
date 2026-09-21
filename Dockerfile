FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir gunicorn
COPY . .
RUN addgroup --system app && adduser --system --ingroup app app && mkdir -p /app/staticfiles /app/media && chown -R app:app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --start-period=30s --retries=3 CMD curl -fsS http://127.0.0.1:8000/healthz/ || exit 1
CMD ["sh","docker-entrypoint.sh","gunicorn","--bind","0.0.0.0:8000","--workers","2","--threads","2","--timeout","60","--access-logfile","-","--error-logfile","-","wsgi:application"]
