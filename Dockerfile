FROM node:24-trixie-slim

# 1) Enable contrib/non-free/non-free-firmware and install runtime deps
RUN set -eux; \
    sed -i 's/^Components:.*/Components: main contrib non-free non-free-firmware/' /etc/apt/sources.list.d/debian.sources; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        git \
        uuid-runtime \
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
        libavcodec-extra \
        ffmpeg \
    && command -v git && git --version \
    && rm -rf /var/lib/apt/lists/*

# Make GitPython find git reliably
ENV GIT_PYTHON_GIT_EXECUTABLE=/usr/bin/git \
    GIT_PYTHON_REFRESH=quiet

# Copy uv (with embedded Python) from the official image to a more standard location
COPY --from=docker.io/astral/uv:latest /uv /uvx /usr/local/bin/

# Stage 2: User and Environment Setup
RUN groupadd -g 1001 appuser \
    && useradd -m -u 1001 -g appuser appuser \
    && mkdir -p /app /ms-playwright /tmp/.X11-unix \
    && chown -R appuser:appuser /app /ms-playwright /tmp/.X11-unix \
    && chmod 1777 /tmp/.X11-unix \
    && chmod -R 777 /ms-playwright

WORKDIR /app
USER appuser

# Stage 3: Python Dependency Installation (Uses caching)
COPY .python-version ./
COPY --chown=appuser:appuser pyproject.toml uv.lock ./
RUN /usr/local/bin/uv sync

# Stage 4: Application Code
COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser .chainlit ./.chainlit
COPY --chown=appuser:appuser public ./public
COPY --chown=appuser:appuser chainlit.md ./chainlit.md



EXPOSE 8000

ENV PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DISPLAY=:1

ENTRYPOINT ["/usr/local/bin/uv", "run", "chainlit", "run", "src/app.py", "--host=0.0.0.0", "--port=8000"]
