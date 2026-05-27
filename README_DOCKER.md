# Deploying KAI API With CLI OAuth (Docker)

The Docker image now runs two local services:

- KAI API on port `7860`
- CLIProxyAPI sidecar on `127.0.0.1:8317`

Playwright/browser providers are disabled by default. Their code remains in the repo, but they are hidden from the UI and skipped at startup unless you explicitly re-enable them.

## Hugging Face Spaces

1. Create or open the `kai-api-gateway` Space.
2. Set the Space SDK to `Docker`.
3. Push this repository to the Space or let the GitHub sync workflow deploy it.
4. Open `https://YOUR_USERNAME-kai-api-gateway.hf.space`.

## CLI OAuth Flow

Use the landing page or API endpoints:

```bash
curl -X POST https://YOUR_HOST/cli/auth/codex/start \
  -H "Authorization: Bearer YOUR_API_KEY"
```

The response contains a login URL. Open it in your browser, finish login, copy the final redirect URL, then submit it:

```bash
curl -X POST https://YOUR_HOST/cli/auth/codex/callback \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"redirect_url":"PASTE_FINAL_BROWSER_REDIRECT_URL_HERE"}'
```

Supported providers are `codex`, `antigravity`, `gemini`, `claude`, `xai`, and `kimi`.

## Chat Examples

```bash
curl https://YOUR_HOST/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"model":"codex-gpt-5.5","messages":[{"role":"user","content":"Hello"}]}'
```

You can list sidecar models with:

```bash
curl https://YOUR_HOST/cli/models \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Environment Flags

`KAI_CLI_PROXY_ENABLED=true` enables the sidecar integration.

`KAI_CLI_PROXY_API_KEY` is the internal key KAI uses to call the sidecar.

`KAI_CLI_PROXY_MANAGEMENT_KEY` protects OAuth and management routes.

`KAI_ENABLE_BROWSER_PROVIDERS=false` keeps Playwright providers off.

`KAI_HIDE_BROWSER_PROVIDERS=true` keeps browser providers out of the admin UI.

`GEMINI_OAUTH_CLIENT_ID` and `GEMINI_OAUTH_CLIENT_SECRET` are required for Gemini CLI OAuth.

`ANTIGRAVITY_OAUTH_CLIENT_ID` and `ANTIGRAVITY_OAUTH_CLIENT_SECRET` are required for Antigravity OAuth.

To bring Playwright providers back later, install Playwright browser dependencies in the image and set:

```bash
KAI_ENABLE_BROWSER_PROVIDERS=true
KAI_HIDE_BROWSER_PROVIDERS=false
```

## Vercel Note

The sidecar needs a long-running Docker process, so the full CLI OAuth setup belongs on Docker hosts such as Hugging Face Spaces, Render, Railway, Koyeb, or EC2. Vercel can still serve the lightweight Python app, but it will not run the Go sidecar.
