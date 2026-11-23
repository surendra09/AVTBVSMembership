# --- AVTBVS Membership API ---------------------------------------------------
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends default-mysql-client \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app && useradd --system --gid app --home /app app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
RUN mkdir -p /data/private && chown -R app:app /data /app
USER app
EXPOSE 8000
# Migrations run in the entrypoint so the schema is always current before serving.
CMD ["sh", "-c", "alembic upgrade head && python -m app.cli init-sequences && gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w ${WEB_CONCURRENCY:-2} -b 0.0.0.0:8000 --forwarded-allow-ips='*' --access-logfile - --timeout 60"]
