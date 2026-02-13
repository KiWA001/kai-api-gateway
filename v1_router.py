from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks
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

async def verify_api_key(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
):
    """
    Verify Bearer Token or X-API-KEY.
    Returns: key_data (dict) or None (if demo key)
    Raises: HTTPException if invalid
    """
    token = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
    
    if not token and x_api_key:
        token = x_api_key
        
    if not token:
        raise HTTPException(status_code=401, detail="Incorrect API Key")

    # 1. Check Demo Key
    if token == DEMO_API_KEY:
        return {"id": "demo", "name": "Demo User", "limit_tokens": -1}

    # 2. Check Database
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Service unavailable")

    try:
        # Check if key exists and is active
        res = supabase.table("api_keys").select("*").eq("token", token).execute()
        
        if not res.data:
             raise HTTPException(status_code=401, detail="Incorrect API key provided")
            
        key_data = res.data[0]
        
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
