FROM node:24-slim

# Install system dependencies for Playwright and Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libglib2.0-0 \
    libnss3 \
    libatk-bridge2.0-0 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    libxshmfence1 \
    libxfixes3 \
    libxkbcommon0 \
    libxext6 \
    libxrender1 \
    libx11-6 \
    libxtst6 \
    libenchant-2-2 \
    libwoff1 \
    libopus0 \
    libwebpdemux2 \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libavcodec-extra59 \
    libavformat59 \
    libswresample4 \
    libvpx7 \
    libevent-2.1-7 \
    libsecret-1-0 \
    libxslt1.1 \
    uuid-runtime \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy uv (with embedded Python) from the official image
COPY --from=docker.io/astral/uv:latest /uv /uvx /bin/

# Create non-root user and group
RUN groupadd -g 1001 appuser && useradd -m -u 1001 -g appuser appuser \
    && mkdir -p /app /ms-playwright /tmp/.X11-unix \
    && chown -R appuser:appuser /app /ms-playwright /tmp/.X11-unix \
    && chmod 1777 /tmp/.X11-unix \
    && chmod -R 777 /ms-playwright

WORKDIR /app

USER appuser

# Copy Python dependency files and install dependencies with uv (as appuser)
COPY --chown=appuser:appuser pyproject.toml uv.lock ./
RUN uv sync

# Copy application code (as appuser)
COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser .chainlit ./.chainlit
COPY --chown=appuser:appuser public ./public

EXPOSE 8000

ENV PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DISPLAY=:1

ENTRYPOINT ["uv", "run", "chainlit", "run", "src/app.py", "--host=0.0.0.0", "--port=8000"]
