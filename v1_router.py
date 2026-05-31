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
from cli_proxy import CLI_MODEL_ALIASES, cli_api_request, is_cli_model_enabled, resolve_cli_model, disable_cli_auth_session
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
    if not is_cli_model_enabled(request.model):
        return openai_error(
            f"Model '{request.model}' is disabled. Enable it in the admin model settings.",
            "model_disabled",
            403,
        )

    try:
        payload = request.model_dump()
        payload["model"] = resolve_cli_model(request.model)
        payload.pop("provider", None)
        
        provider_id = cli_model_provider(request.model)
        headers = {
            "content-type": "application/json",
            "X-CLI-Auth-Provider": provider_id
        }
        
        response = None
        max_retries = 3
        for attempt in range(max_retries):
            response = await cli_api_request(
                "POST",
                "v1/chat/completions",
                json_body=payload,
                headers=headers,
            )
            
            # Check for authentication errors that warrant a retry with a different session
            should_retry = False
            try:
                data = response.json()
                error_obj = data.get("error", {})
                error_msg = str(error_obj.get("message", "")).lower()
                error_code = str(error_obj.get("code", "")).lower()
                
                # Detect common "invalidated token" or "auth unavailable" patterns
                if response.status_code in {401, 403} or "invalidated" in error_msg or "auth_unavailable" in error_code:
                    should_retry = True
            except Exception:
                if response.status_code in {401, 403}:
                    should_retry = True

            if should_retry:
                auth_id = response.headers.get("X-CLI-Auth-ID")
                if auth_id:
                    print(f"Auth error detected for session {auth_id} (Attempt {attempt+1}/{max_retries}). Disabling session and retrying...")
                    await disable_cli_auth_session(auth_id)
                    continue
            
            # If we reached here, either it was successful or we can't automate a retry
            break

        if not response:
            return error_server("CLI proxy request failed: No response received")

        try:
            data = response.json()
        except Exception:
            return openai_error(
                response.text or "CLI proxy returned a non-JSON response",
                "upstream_error",
                response.status_code,
            )

        if response.status_code >= 400:
            return JSONResponse(data, status_code=response.status_code)

        response_text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        usage = data.get("usage") or calculate_usage([m.model_dump() for m in request.messages], response_text)
        if not key_data.get("is_dashboard", False):
            background_tasks.add_task(update_usage_stats, key_data["id"], usage.get("total_tokens", 0))
        return JSONResponse(data)
    except Exception as e:
        return error_server(f"CLI proxy request failed: {e}")
