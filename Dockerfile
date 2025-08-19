FROM python:3.11-slim

# 1. System dependencies for Playwright & Xvfb
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    xvfb \
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
    libavcodec59 \
    libavformat59 \
    libswresample4 \
    libvpx7 \
    libevent-2.1-7 \
    libsecret-1-0 \
    libxslt1.1 \
    uuid-runtime \
    git \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Node.js and npm (so npx is always available)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get update && apt-get install -y --no-install-recommends nodejs \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# 3. Create non-root user and group, and fix X11 permissions
RUN groupadd -r appuser && useradd -m -r -g appuser appuser \
    && mkdir -p /app /tmp/.X11-unix \
    && chmod 1777 /tmp/.X11-unix

WORKDIR /app

# 4. ENV vars
ENV PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DISPLAY=:1

# 5. Install uv (Python dependency manager)
RUN curl -Ls https://astral.sh/uv/install.sh | sh \
 && cp /root/.local/bin/uv /usr/local/bin/uv \
 && cp /root/.local/bin/uvx /usr/local/bin/uvx \
 && chmod 755 /usr/local/bin/uv /usr/local/bin/uvx \
 && rm -rf /root/.local

# 6. Install Python dependencies
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# 7. Install Node.js dependencies for playwright-mcp
COPY playwright-mcp/package*.json ./playwright-mcp/
WORKDIR /app/playwright-mcp
RUN npm install \
 && npm install @playwright/mcp@0.0.29 playwright@1.44.0

# 8. Install Playwright browsers and fix .bin permissions
RUN npx playwright install --with-deps \
 && npx --prefix ./node_modules/@playwright/mcp playwright install --with-deps || true \
 && chmod -R 755 /app/playwright-mcp/node_modules/.bin \
 && find /app/playwright-mcp/node_modules/.bin -type f -exec chmod +x {} \;

WORKDIR /app

# 9. Copy application code, remove config.yaml if present
COPY . ./
RUN rm -f /app/config.yaml || true

# 10. Copy node_modules up for global npx if needed
RUN cp -r /app/playwright-mcp/node_modules /app/node_modules \
 && chmod -R 755 /app/node_modules/.bin \
 && find /app/node_modules/.bin -type f -exec chmod +x {} \;

# 11. Make sure all users can write to the Playwright browser cache
RUN mkdir -p /ms-playwright && chmod -R 777 /ms-playwright

# 12. Prebuild readabilipy's Javascript dependencies and fix permissions
RUN if [ -d "/usr/local/lib/python3.11/site-packages/readabilipy/javascript" ]; then \
      cd /usr/local/lib/python3.11/site-packages/readabilipy/javascript \
      && npm install \
      && chown -R appuser:appuser /usr/local/lib/python3.11/site-packages/readabilipy/javascript; \
    fi

# 13. Fix permissions for appuser everywhere
RUN chown -R appuser:appuser /app /ms-playwright

USER appuser

EXPOSE 8000

ENTRYPOINT bash -c "Xvfb :1 -screen 0 1280x720x24 & sleep 2 && exec chainlit run src/app.py --host=0.0.0.0 --port=8000"