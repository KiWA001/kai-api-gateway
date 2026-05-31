from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any
import time
import uuid

from auth import verify_api_key
from auth_cache import increment_cached_usage
from db import get_supabase
from local_db import increment_usage as local_increment_usage
from services import engine
from utils import calculate_usage
from cli_proxy import CLI_MODEL_ALIASES, cli_api_request, is_cli_model_enabled, resolve_cli_model, disable_cli_auth_session, cli_model_provider
from error_handling import (
    openai_error,
    error_invalid_api_key,
    error_quota_exceeded,
    error_model_not_found,
    error_server
)

# Initialize Router
router = APIRouter()
# engine is imported from services

# --- Pydantic Models (OpenAI Spec) ---

class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    
    # Custom fields for our API (optional)
    provider: Optional[str] = None 

class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = "stop"

class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: UsageInfo


# --- Background Task for Usage Update ---

def update_usage_stats(key_id: str, tokens: int):
    """Increment token usage in DB."""
    if key_id == "demo" or key_id == "dashboard":
        return # Don't track demo/dashboard usage
    increment_cached_usage(key_id, tokens)
        
    supabase = get_supabase()
    if supabase and tokens > 0:
        try:
            current = supabase.table("kaiapi_api_keys").select("usage_tokens").eq("id", key_id).execute()
            if current.data:
                new_total = (current.data[0]['usage_tokens'] or 0) + tokens
                supabase.table("kaiapi_api_keys").update({"usage_tokens": new_total}).eq("id", key_id).execute()
                
        except Exception as e:
            print(f"Failed to update usage for {key_id}: {e}")
            local_increment_usage(key_id, tokens)
    else:
        local_increment_usage(key_id, tokens)

# --- Endpoint ---

@router.get("/v1/debug")
async def v1_debug():
    """Debug endpoint to verify router is mounted."""
    return {"status": "ok", "message": "v1 router is matching"}

@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest, 
    background_tasks: BackgroundTasks,
    key_data: dict = Depends(verify_api_key)
):
    """
    OpenAI-compatible Chat Completion Endpoint.
    """
    provider_id = cli_model_provider(request.model)
    resolved_model = resolve_cli_model(request.model)

    # Validate that we have a known provider prefix
    if provider_id == "cli":
        return openai_error(
            f"Cannot determine provider for model '{request.model}'. "
            f"Use a provider prefix like 'codex-', 'gemini-', 'claude-', 'antigravity-', 'xai-', or 'kimi-' "
            f"(e.g. 'codex-gpt-4o').",
            "unknown_provider",
            400,
        )

    try:
        payload = request.model_dump()
        payload["model"] = resolved_model
        payload.pop("provider", None)

        headers = {
            "content-type": "application/json",
            "X-CLI-Auth-Provider": provider_id,
        }

        response = None
        auth_errors = []
        max_retries = 3

        for attempt in range(max_retries):
            try:
                response = await cli_api_request(
                    "POST",
                    "v1/chat/completions",
                    json_body=payload,
                    headers=headers,
                )
            except Exception as conn_err:
                return openai_error(
                    f"Gateway could not reach the CLI sidecar. "
                    f"Check that KAI_CLI_PROXY_URL is correct and the sidecar is running. "
                    f"Detail: {conn_err}",
                    "sidecar_unreachable",
                    503,
                )

            # Parse response to check for retryable auth errors
            should_retry = False
            try:
                data = response.json()
                error_obj = data.get("error", {})
                error_msg = str(error_obj.get("message", "")).lower()
                error_code = str(error_obj.get("code", "")).lower()

                # Detect auth invalidation patterns
                if response.status_code in {401, 403} or "invalidated" in error_msg or "auth_unavailable" in error_code:
                    should_retry = True
                    auth_errors.append(error_obj.get("message", "auth_unavailable"))
            except Exception:
                if response.status_code in {401, 403}:
                    should_retry = True
                    auth_errors.append(f"HTTP {response.status_code}")

            if should_retry:
                auth_id = response.headers.get("X-CLI-Auth-ID")
                if auth_id:
                    print(f"[kai-gateway] Auth error for session {auth_id} on attempt {attempt+1}/{max_retries} "
                          f"(provider={provider_id}, model={resolved_model}). Disabling and retrying.")
                    await disable_cli_auth_session(auth_id)
                    continue
                else:
                    # Auth error but no session ID — can't rotate, fail fast
                    return openai_error(
                        f"Provider '{provider_id}' returned an authentication error but no session ID was provided "
                        f"in X-CLI-Auth-ID. Cannot rotate session. "
                        f"Detail: {auth_errors[-1] if auth_errors else 'unknown'}",
                        "auth_error_no_session",
                        401,
                    )

            # Non-retryable — break out
            break

        if not response:
            return openai_error(
                f"CLI sidecar returned no response after {max_retries} attempts "
                f"(provider={provider_id}, model={resolved_model}). "
                f"This usually means all sessions for '{provider_id}' are exhausted or disabled.",
                "no_sessions_available",
                503,
            )

        # If we exhausted all retries still hitting auth errors
        if should_retry and auth_errors:
            return openai_error(
                f"All {max_retries} '{provider_id}' sessions failed with authentication errors. "
                f"Please add or re-authenticate a '{provider_id}' session via the dashboard. "
                f"Last error: {auth_errors[-1]}",
                "all_sessions_exhausted",
                401,
            )

        # Parse the body
        try:
            data = response.json()
        except Exception:
            return openai_error(
                f"CLI sidecar returned non-JSON response (HTTP {response.status_code}). "
                f"Raw body: {response.text[:300] if response.text else '(empty)'}",
                "sidecar_bad_response",
                502,
            )

        # Upstream error — pass it through with context added
        if response.status_code >= 400:
            # Enrich error message if it's a generic sidecar error
            upstream_error = data.get("error", {})
            upstream_msg = upstream_error.get("message", "")
            if "unknown provider" in upstream_msg.lower():
                upstream_error["message"] = (
                    f"The CLI sidecar does not have an executor registered for provider '{provider_id}'. "
                    f"Ensure the sidecar is built with support for this provider and has at least one active auth session. "
                    f"Original: {upstream_msg}"
                )
                data["error"] = upstream_error
            elif "auth_not_found" in str(upstream_error.get("code", "")).lower() or "auth_unavailable" in str(upstream_error.get("code", "")).lower():
                upstream_error["message"] = (
                    f"No active '{provider_id}' session found in the sidecar. "
                    f"Log in via the dashboard (/), or check that your auth files are present. "
                    f"Original: {upstream_msg}"
                )
                data["error"] = upstream_error

            return JSONResponse(data, status_code=response.status_code)

        # Success — track usage
        response_text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        usage = data.get("usage") or calculate_usage(
            [m.model_dump() for m in request.messages], response_text
        )
        if not key_data.get("is_dashboard", False):
            background_tasks.add_task(
                update_usage_stats, key_data["id"], usage.get("total_tokens", 0)
            )
        return JSONResponse(data)

    except Exception as e:
        return error_server(
            f"Unexpected error in gateway while processing model '{request.model}' "
            f"via provider '{provider_id}': {type(e).__name__}: {e}"
        )
