FROM node:22-alpine AS ui-build

WORKDIR /ui

COPY hive/ui/package.json hive/ui/package-lock.json ./
RUN npm ci
COPY hive/ui ./
RUN npm run build

FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    GIT_TERMINAL_PROMPT=0

ARG TARGETARCH=amd64
ARG KUBECTL_VERSION=v1.37.0
ARG FLUX_VERSION=2.4.0
ARG HELM_VERSION=3.22.0
COPY scripts/install-tools.sh /tmp/install-tools.sh
RUN sh /tmp/install-tools.sh && rm /tmp/install-tools.sh

COPY packages/core /tmp/core
COPY hive/pyproject.toml ./
COPY hive/src ./src
COPY hive/infra/config /etc/hive
COPY --from=ui-build /ui/dist ./ui/dist
RUN pip install --no-cache-dir /tmp/core . \
    && useradd --uid 65532 --create-home --shell /usr/sbin/nologin hive

USER 65532:65532
EXPOSE 8070
CMD ["uvicorn", "hive.server:app", "--app-dir", "/app/src", "--host", "0.0.0.0", "--port", "8070"]
