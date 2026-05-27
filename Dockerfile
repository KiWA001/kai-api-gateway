FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    HOME=/tmp/kai-home \
    PORT=7860 \
    KAI_ENABLE_BROWSER_PROVIDERS=false \
    KAI_HIDE_BROWSER_PROVIDERS=true \
    KAI_CLI_PROXY_ENABLED=true \
    KAI_CLI_PROXY_URL=http://127.0.0.1:8317 \
    KAI_CLI_PROXY_API_KEY=sk-kai-cli-proxy \
    KAI_CLI_PROXY_MANAGEMENT_KEY=sk-kai-cli-management \
    KAI_CLI_PROXY_CONFIG_PATH=/tmp/cliproxy/config.yaml \
    KAI_CLI_PROXY_AUTH_DIR=/tmp/cliproxy/auths \
    GEMINI_OAUTH_CLIENT_ID= \
    GEMINI_OAUTH_CLIENT_SECRET= \
    ANTIGRAVITY_OAUTH_CLIENT_ID= \
    ANTIGRAVITY_OAUTH_CLIENT_SECRET=

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY CLIProxyAPI-linux-amd64 /usr/local/bin/CLIProxyAPI
COPY . .

RUN chmod +x /app/start-container.sh /usr/local/bin/CLIProxyAPI

EXPOSE 7860

CMD ["/app/start-container.sh"]
