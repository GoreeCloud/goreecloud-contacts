ARG NODE_IMAGE=node:24-bookworm-slim@sha256:6f7b03f7c2c8e2e784dcf9295400527b9b1270fd37b7e9a7285cf83b6951452d
ARG PYTHON_IMAGE=python:3.13-slim-bookworm@sha256:6771159cd4fa5d9bba1258caf0b82e6b73458c694d178ad97c5e925c2d0e1a91

FROM ${NODE_IMAGE} AS frontend-build
WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY artwork/ /build/artwork/
COPY frontend/ ./
RUN npm run validate:ui && npm run build

FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN groupadd --gid 10001 goreecloud \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin goreecloud

WORKDIR /app/backend
COPY backend/pyproject.toml backend/requirements.runtime.lock ./
COPY backend/app ./app
RUN python -m pip install --no-cache-dir -r requirements.runtime.lock \
    && python -m pip install --no-cache-dir --no-deps . \
    && python -m pip check

COPY --from=frontend-build /build/frontend/dist /app/frontend

RUN mkdir -p /data /tmp /run/secrets \
    && chown -R 10001:10001 /data /tmp \
    && chmod 0755 /run/secrets

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health/ready', timeout=3).read()"]

CMD ["python", "-m", "uvicorn", "app.production:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--limit-concurrency", "100", "--backlog", "128", "--timeout-keep-alive", "5"]
