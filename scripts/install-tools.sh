#!/bin/sh
set -eu

apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git jq openssh-client passwd \
    && curl --fail --location --proto '=https' --tlsv1.2 --retry 3 -o /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl" \
    && curl --fail --location --proto '=https' --tlsv1.2 --retry 3 -o /tmp/kubectl.sha256 "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl.sha256" \
    && echo "$(cat /tmp/kubectl.sha256)  /usr/local/bin/kubectl" | sha256sum -c - \
    && chmod 0755 /usr/local/bin/kubectl \
    && curl --fail --location --proto '=https' --tlsv1.2 --retry 3 -o /tmp/flux.tar.gz "https://github.com/fluxcd/flux2/releases/download/v${FLUX_VERSION}/flux_${FLUX_VERSION}_linux_${TARGETARCH}.tar.gz" \
    && curl --fail --location --proto '=https' --tlsv1.2 --retry 3 -o /tmp/flux_checksums.txt "https://github.com/fluxcd/flux2/releases/download/v${FLUX_VERSION}/flux_${FLUX_VERSION}_checksums.txt" \
    && grep "flux_${FLUX_VERSION}_linux_${TARGETARCH}.tar.gz$" /tmp/flux_checksums.txt | sed "s|  flux_${FLUX_VERSION}_linux_${TARGETARCH}.tar.gz$|  /tmp/flux.tar.gz|" | sha256sum -c - \
    && tar -xzf /tmp/flux.tar.gz -C /usr/local/bin flux \
    && curl --fail --location --proto '=https' --tlsv1.2 --retry 3 -o /tmp/helm.tar.gz "https://get.helm.sh/helm-v${HELM_VERSION}-linux-${TARGETARCH}.tar.gz" \
    && curl --fail --location --proto '=https' --tlsv1.2 --retry 3 -o /tmp/helm.sha256 "https://get.helm.sh/helm-v${HELM_VERSION}-linux-${TARGETARCH}.tar.gz.sha256sum" \
    && echo "$(awk '{print $1}' /tmp/helm.sha256)  /tmp/helm.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/helm.tar.gz --strip-components=1 -C /usr/local/bin "linux-${TARGETARCH}/helm" \
    && apt-get purge -y --auto-remove curl \
    && rm -f /tmp/kubectl.sha256 /tmp/flux.tar.gz /tmp/flux_checksums.txt /tmp/helm.tar.gz /tmp/helm.sha256 \
    && rm -rf /var/lib/apt/lists/*
