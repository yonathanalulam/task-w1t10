FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl openssl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

COPY backend /app
COPY ops/scripts/generate_local_certs.sh /opt/trailforge/generate_local_certs.sh

RUN chmod +x /app/scripts/entrypoint.sh /opt/trailforge/generate_local_certs.sh

EXPOSE 8443

CMD ["/app/scripts/entrypoint.sh"]
