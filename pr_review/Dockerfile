FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GIT_TERMINAL_PROMPT=0
ARG TARGETARCH=amd64
ARG KUBECTL_VERSION=v1.37.0

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git \
    && curl -fsSL -o /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl" \
    && curl -fsSL -o /tmp/kubectl.sha256 "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl.sha256" \
    && echo "$(cat /tmp/kubectl.sha256)  /usr/local/bin/kubectl" | sha256sum -c - \
    && chmod 0755 /usr/local/bin/kubectl \
    && rm /tmp/kubectl.sha256 \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*

COPY packages/core /tmp/core
COPY pr_review/pyproject.toml ./
COPY pr_review/src ./src
COPY pr_review/infra/config /etc/pr-review
RUN pip install --no-cache-dir /tmp/core . \
    && groupadd --gid 65532 pr-review \
    && useradd --uid 65532 --gid 65532 --home-dir /home/pr-review --create-home --shell /usr/sbin/nologin pr-review \
    && mkdir -p /tmp/pr_review \
    && chown -R 65532:65532 /tmp/pr_review

USER 65532:65532
EXPOSE 8090
CMD ["uvicorn", "pr_review.server:app", "--host", "0.0.0.0", "--port", "8090"]
