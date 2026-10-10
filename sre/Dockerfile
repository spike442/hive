FROM python:3.12-slim

WORKDIR /app
ENV PATH=/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TERM=dumb \
    GIT_TERMINAL_PROMPT=0
ARG TARGETARCH=amd64
ARG KUBECTL_VERSION=v1.37.0
ARG FLUX_VERSION=2.4.0
ARG HELM_VERSION=3.22.0

COPY scripts/install-tools.sh /tmp/install-tools.sh
RUN sh /tmp/install-tools.sh && rm /tmp/install-tools.sh

COPY packages/core /tmp/core
COPY sre/pyproject.toml ./
COPY sre/infra/config /etc/sre/config
COPY sre/src ./src
RUN groupadd --gid 65532 sre \
    && useradd --uid 65532 --gid 65532 --home-dir /home/sre --create-home --shell /usr/sbin/nologin sre \
    && pip install --no-cache-dir /tmp/core . \
    && mkdir -p /home/sre \
    && chown -R 65532:65532 /home/sre

USER 65532:65532
CMD ["uvicorn", "sre.server:app", "--app-dir", "/app/src", "--host", "0.0.0.0", "--port", "8080"]
