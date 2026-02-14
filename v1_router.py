from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any
import time
import uuid

from config import DEMO_API_KEY
from db import get_supabase
from services import engine
from utils import calculate_usage
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


# --- Auth Dependency ---

# List of allowed origins/paths that don't need API key (dashboard access)
DASHBOARD_PATHS = ["/", "/docs/public", "/docs", "/static/"]
DASHBOARD_HOSTS = ["localhost", "127.0.0.1"]  # Add your domain here when deployed

async def verify_api_key(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
):
    """
    Verify Bearer Token or X-API-KEY.
    Dashboard requests (from same origin) don't need API key.
    External API calls require API key.
    Returns: key_data (dict) 
    Raises: HTTPException if invalid
    """
    token = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
    
    if not token and x_api_key:
        token = x_api_key
    
    # Check if request is coming from dashboard (same origin)
    referer = request.headers.get("referer", "")
    origin = request.headers.get("origin", "")
    
    # Check if referer/origin matches dashboard
    is_dashboard_request = False
    
    # Check if referer contains dashboard paths
    for path in DASHBOARD_PATHS:
        if path in referer:
            is_dashboard_request = True
            break
    
    # Also check if origin is localhost (local development)
    for host in DASHBOARD_HOSTS:
        if host in origin or host in referer:
            is_dashboard_request = True
            break
    
    # Check if it's a browser request (has Accept: text/html)
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header and (referer or origin):
        is_dashboard_request = True
    
    if not token:
        if is_dashboard_request:
            # Dashboard access - no key needed
            return {"id": "dashboard", "name": "Dashboard User", "limit_tokens": -1}
        else:
            # External API call - key required
            raise HTTPException(
                status_code=401, 
                detail="Authorization header required. Use 'Authorization: Bearer YOUR_API_KEY'. Get a key from the dashboard."
            )

    # 1. Check Demo Key
    if token == DEMO_API_KEY:
        return {"id": "demo", "name": "Demo User", "limit_tokens": -1}

    # 2. Check Database (Non-blocking)
    import asyncio
    loop = asyncio.get_event_loop()
    
    def _sync_check():
        supabase = get_supabase()
        if not supabase:
             # If DB down, allow access as public/demo? Or fail?
             # Fail safe: 503
             raise HTTPException(status_code=503, detail="Service unavailable")
             
        res = supabase.table("api_keys").select("*").eq("token", token).execute()
        if not res.data:
            return None
        return res.data[0]

    try:
        key_data = await loop.run_in_executor(None, _sync_check)
        
        if not key_data:
             raise HTTPException(status_code=401, detail="Incorrect API key provided")
        
        if not key_data.get("is_active", True):
            raise HTTPException(status_code=403, detail="API Key is inactive")
            
        # Check limits
        current_usage = key_data.get("usage_tokens", 0)
        limit = key_data.get("limit_tokens", 0)
        
        if limit > 0 and current_usage >= limit:
             raise HTTPException(status_code=429, detail="You have exceeded your current quota")
             
        return key_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"Auth Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    except HTTPException:
        raise
    except Exception as e:
        print(f"Auth Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# --- Background Task for Usage Update ---

def update_usage_stats(key_id: str, tokens: int):
    """Increment token usage in DB."""
    if key_id == "demo":
        return # Don't track demo usage in DB (or maybe track in a separate table later)
        
    supabase = get_supabase()
    if supabase and tokens > 0:
        try:
            # Atomic increment? Supabase (Postgres) supports it via RPC or simple update if inaccurate is okay.
            # Best practice: use RPC. For now simple update read-modify-write (concurrency risk but okay for low volume)
            # Actually, let's just do a simple increment if possible, or fetch-add
            
            # Since we can't easily do RPC without creating it in SQL first, let's just do Python-side increment
            # (Valid since we have the key_data from verification, but it might be stale)
            
            # Better: create an RPC function later. For now, just logging it.
            # The implementation plan implied we track it.
            
            # Let's try to get fresh usage and update.
            current = supabase.table("api_keys").select("usage_tokens").eq("id", key_id).execute()
            if current.data:
                new_total = (current.data[0]['usage_tokens'] or 0) + tokens
                supabase.table("api_keys").update({"usage_tokens": new_total}).eq("id", key_id).execute()
                
        except Exception as e:
            print(f"Failed to update usage for {key_id}: {e}")

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
    # Convert messages list to simple prompt (or keep as list if engine supports it)
    # Our engine currently takes a single prompt string + optional system prompt.
    
    system_prompt = None
    user_prompt = ""
    
    # Simple conversion logic
    for m in request.messages:
        if m.role == "system":
            system_prompt = m.content
        elif m.role == "user":
            if user_prompt:
                user_prompt += f"\n\n[User]: {m.content}"
            else:
                user_prompt = m.content
        elif m.role == "assistant":
            user_prompt += f"\n\n[Assistant]: {m.content}"
            
    # Call Engine
    provider = request.provider or "auto"
    
    try:
        if not engine:
            raise HTTPException(status_code=503, detail="AI Engine is not initialized (Startup Error)")
            
        result = await engine.chat(
            prompt=user_prompt,
            model=request.model,
            provider=provider,
            system_prompt=system_prompt
        )
        
        response_text = result["response"]
        actual_model = result["model"]
        
        # Calculate Usage
        usage = calculate_usage([m.dict() for m in request.messages], response_text)
        
        # Background: Update DB
        background_tasks.add_task(update_usage_stats, key_data["id"], usage["total_tokens"])
        
        # Construct Response
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=actual_model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=response_text),
                    finish_reason="stop"
                )
            ],
            usage=UsageInfo(**usage)
        )

    except ValueError as e:
        # Invalid model or params
        # We need to return the JSON response object, but we are inside an async endpoint.
        # Direct return works!
        return error_model_not_found(request.model) if "model" in str(e) else openai_error(str(e), "invalid_request_error")
        
    except Exception as e:
        return error_server(str(e))
