# KAI API

**Free AI Proxy API** — no signup, no API keys required on the AI side.

Send a message, get an AI response from GPT-4o, Claude, Llama, Mistral, and more.

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

### `POST /chat` — Send a message

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is quantum computing?",
    "model": "gpt-4o-mini",
    "provider": "auto"
  }'
```

**Response:**
```json
{
  "response": "Quantum computing is...",
  "model": "gpt-4o-mini",
  "provider": "g4f",
  "timestamp": "2026-02-11T21:30:00Z"
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|---|---|---|---|
| `message` | string | ✅ | Your prompt/question |
| `model` | string | ❌ | Model to use (default: `gpt-4o-mini`) |
| `provider` | string | ❌ | `auto`, `g4f`, or `pollinations` |
| `system_prompt` | string | ❌ | System instructions for the AI |

### `GET /models` — List available models

```bash
curl http://localhost:8000/models
```

### `GET /health` — Health check

```bash
curl http://localhost:8000/health
```

## Providers

| Provider | Models | How it works |
|---|---|---|
| **g4f** | GPT-4o, GPT-4o-mini, Claude 3.5, Llama, Mixtral | Routes through third-party sites, no API key |
| **Pollinations** | OpenAI, Mistral, Llama, DeepSeek, Claude | Free public AI API, no auth |

## Architecture

- **Stateless**: Every request creates a fresh session — no conversation history
- **Multi-provider fallback**: If g4f fails, Pollinations picks up
- **Provider priority**: g4f → Pollinations

## Integration Examples

### Python
```python
import requests

response = requests.post("http://localhost:8000/chat", json={
    "message": "Explain AI in one sentence"
})
print(response.json()["response"])
```

### JavaScript
```javascript
const response = await fetch("http://localhost:8000/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ message: "Explain AI in one sentence" })
});
const data = await response.json();
console.log(data.response);
```
