# Deploying KAI API With CLI OAuth

The Docker image runs:

- KAI API on port `7860`
- CLIProxyAPI sidecar on `127.0.0.1:8317`

## Hugging Face Spaces

1. Create a Docker Space.
2. Push this repository to the Space or connect GitHub sync.
3. Set any required OAuth client environment variables.
4. Open `/qazmlp` to manage API keys, OAuth sessions, and enabled models.

## Environment

`KAI_CLI_PROXY_ENABLED=true` enables the sidecar integration.

`KAI_CLI_PROXY_API_KEY` is the internal key KAI uses to call the sidecar.

`KAI_CLI_PROXY_MANAGEMENT_KEY` protects OAuth and management routes.

`GEMINI_OAUTH_CLIENT_ID` and `GEMINI_OAUTH_CLIENT_SECRET` are required for Gemini CLI OAuth.

`ANTIGRAVITY_OAUTH_CLIENT_ID` and `ANTIGRAVITY_OAUTH_CLIENT_SECRET` are required for Anti-Gravity OAuth.
