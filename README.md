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

**Free AI Proxy API** with Docker-based CLI OAuth support.

Send a message to OpenAI-compatible endpoints and route through free fallbacks or OAuth-backed CLI providers such as Codex, Antigravity, Gemini CLI, Claude Code, xAI, and Kimi.

## Quick Start

```bash
# Create + activate virtual environment
cd KAI_API
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --host 0.0.0.0 --port 8000

# Open interactive docs
open http://localhost:8000/docs
```

## API Endpoints

### `POST /v1/chat/completions` — Send a message

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-kai-demo-public" \
  -d '{
    "model": "cliproxy-codex-gpt-5.5",
    "messages": [{"role": "user", "content": "What is quantum computing?"}]
  }'
```

**Response:**
```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "cliproxy-codex-gpt-5.5",
  "choices": [{"message": {"role": "assistant", "content": "Quantum computing is..."}}],
  "usage": {"prompt_tokens": 8, "completion_tokens": 42, "total_tokens": 50}
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|---|---|---|---|
| `messages` | array | ✅ | OpenAI-compatible chat messages |
| `model` | string | ✅ | Model alias such as `cliproxy-codex-gpt-5.5` |
| `provider` | string | ❌ | `auto`, `cli`, `g4f`, or `pollinations` |

### `POST /cli/auth/{provider}/start` — Start manual OAuth

```bash
curl -X POST http://localhost:8000/cli/auth/codex/start \
  -H "Authorization: Bearer sk-kai-demo-public"
```

Open the returned URL in your browser. After login, paste the final redirect URL into:

```bash
curl -X POST http://localhost:8000/cli/auth/codex/callback \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-kai-demo-public" \
  -d '{"redirect_url":"PASTE_FINAL_BROWSER_REDIRECT_URL_HERE"}'
```

Supported provider IDs: `codex`, `antigravity`, `gemini`, `claude`, `xai`, `kimi`.

Gemini CLI and Antigravity OAuth require their Google OAuth client ID/secret in environment variables on the Docker host.

### `GET /models` — List available models

```bash
curl http://localhost:8000/models
```

### `GET /cli/models` — List CLI sidecar models

```bash
curl http://localhost:8000/cli/models \
  -H "Authorization: Bearer sk-kai-demo-public"
```

### `GET /health` — Health check

```bash
curl http://localhost:8000/health
```

## Providers

| Provider | Models | How it works |
|---|---|---|
| **CLI Proxy OAuth** | GPT-5.5, Claude Opus 4.7, Gemini 3.5 Flash, Grok 4.3, Kimi K2.6 | Local CLIProxyAPI sidecar with manual OAuth login |
| **g4f** | GPT-4o, GPT-4o-mini, Claude 3.5, Llama, Mixtral | Routes through third-party sites, no API key |
| **Pollinations** | OpenAI, Mistral, Llama, DeepSeek, Claude | Free public AI API, no auth |

Browser/Playwright providers are disabled and hidden by default. Re-enable later with:

```bash
KAI_ENABLE_BROWSER_PROVIDERS=true
KAI_HIDE_BROWSER_PROVIDERS=false
```

## Architecture

- **Stateless**: Every request creates a fresh session — no conversation history
- **Multi-provider fallback**: If one enabled provider fails, the next ranked provider is tried
- **Provider priority**: CLI OAuth in Docker, then API/free fallbacks

## Integration Examples

### Python
```python
import requests

response = requests.post("http://localhost:8000/v1/chat/completions", json={
    "model": "cliproxy-codex-gpt-5.5",
    "messages": [{"role": "user", "content": "Explain AI in one sentence"}]
})
print(response.json()["choices"][0]["message"]["content"])
```

### JavaScript
```javascript
const response = await fetch("http://localhost:8000/v1/chat/completions", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    model: "cliproxy-codex-gpt-5.5",
    messages: [{ role: "user", content: "Explain AI in one sentence" }]
  })
});
const data = await response.json();
console.log(data.choices[0].message.content);
```
