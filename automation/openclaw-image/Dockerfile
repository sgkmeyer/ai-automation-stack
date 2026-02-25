FROM alpine/openclaw:latest

USER root
ENV PIP_BREAK_SYSTEM_PACKAGES=1

# Pin Openclaw version (base image may lag behind latest release).
# To upgrade: change this version, rebuild, and redeploy.
# The gateway entrypoint runs /app/openclaw.mjs, so we must replace /app contents.
ARG OPENCLAW_VERSION=2026.2.24
RUN npm i -g "openclaw@${OPENCLAW_VERSION}" && \
    rm -rf /app/* && \
    cp -a /usr/local/lib/node_modules/openclaw/. /app/

# Install Python tooling in a distro-agnostic way (Debian/Ubuntu or Alpine base images).
RUN set -eux; \
    if command -v apt-get >/dev/null 2>&1; then \
      apt-get update; \
      apt-get install -y --no-install-recommends python3 python3-pip ca-certificates; \
      rm -rf /var/lib/apt/lists/*; \
    elif command -v apk >/dev/null 2>&1; then \
      apk add --no-cache python3 py3-pip ca-certificates; \
    else \
      echo "No supported package manager found" >&2; \
      exit 1; \
    fi

COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /tmp/requirements.txt

USER node
