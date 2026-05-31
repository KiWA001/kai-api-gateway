---
title: KAI API Gateway
emoji: 🦀
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
app_port: 7860
---

# KAI API

OpenAI-compatible gateway for CLI OAuth models only.

The app runs a small FastAPI service plus a local CLIProxyAPI sidecar. Supported OAuth providers are Codex, Anti-Gravity, Gemini CLI, Claude Code, xAI, and Kimi.

## Endpoints

```bash
GET  /models
GET  /health
POST /v1/chat/completions
POST /cli/auth/{provider}/start
POST /cli/auth/{provider}/callback
GET  /cli/auth/files
```

## Chat Example

```bash
curl https://YOUR_HOST/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"model":"codex-gpt-5.5","messages":[{"role":"user","content":"Hello"}]}'
```

## OAuth

Use `/qazmlp` for the admin page. It lets you start OAuth sessions, copy the login URL, paste the returned redirect URL, inspect saved sessions, and choose which CLI models are enabled.

Supported provider IDs: `codex`, `antigravity`, `gemini`, `claude`, `xai`, `kimi`.
