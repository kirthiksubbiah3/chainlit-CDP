FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/app \
    UV_CACHE_DIR=/home/app/.cache/uv

# Create user/group with the same IDs as your pod
ARG APP_UID=1001
ARG APP_GID=1001
RUN groupadd -g ${APP_GID} app && useradd -m -u ${APP_UID} -g ${APP_GID} -s /bin/bash app

WORKDIR /app

# Install OS deps
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
       ca-certificates curl git \
       libglib2.0-0 libpango-1.0-0 libpangoft2-1.0-0 \
       libcairo2 libgdk-pixbuf-2.0-0 \
       libffi8 libxml2 libxslt1.1 \
       fonts-dejavu fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Prepare dirs and ownership
RUN mkdir -p /home/app/.cache/uv /app/.venv \
    && chown -R app:app /home/app /app

# Switch to non-root for the rest
USER app

# Ensure venv on PATH if uv creates one in /app/.venv
ENV VIRTUAL_ENV=/app/.venv \
    PATH=/app/.venv/bin:${PATH}

# Copy manifests and sync deps
COPY --chown=app:app pyproject.toml uv.lock* ./
RUN uv sync --no-dev

# Copy app code
COPY --chown=app:app src ./src
COPY --chown=app:app config.yaml ./config.yaml
COPY --chown=app:app .chainlit ./.chainlit
COPY --chown=app:app public ./public
COPY --chown=app:app chainlit.md ./chainlit.md

EXPOSE 8000
CMD ["uv", "run", "chainlit", "run", "src/app.py", "--host", "0.0.0.0", "--port", "8000"]
