from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import secrets
import uuid

from db import get_supabase

router = APIRouter(prefix="/admin", tags=["Admin"])

# --- Models ---

class APIKey(BaseModel):
    id: str
    name: str
    token: str
    usage_tokens: int
    limit_tokens: int
    created_at: str
    is_active: bool

class CreateKeyRequest(BaseModel):
    name: str
    limit_tokens: Optional[int] = 1000000

# --- Endpoints ---

@router.get("/keys", response_model=List[APIKey])
async def list_keys():
    """List all API keys."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    try:
        res = supabase.table("api_keys").select("*").order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/keys", response_model=APIKey)
async def create_key(req: CreateKeyRequest):
    """Create a new API key."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    # Generate a secure token
    token = f"sk-kai-{secrets.token_urlsafe(16)}"
    
    new_key = {
        "name": req.name,
        "token": token,
        "limit_tokens": req.limit_tokens,
        "usage_tokens": 0,
        "is_active": True
    }
    
    try:
        res = supabase.table("api_keys").insert(new_key).execute()
        if res.data:
            return res.data[0]
        raise HTTPException(status_code=500, detail="Failed to create key")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/keys/{key_id}")
async def revoke_key(key_id: str):
    """Revoke (delete) an API key."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    try:
        # Check if exists first? Or just delete.
        # Hard delete for now, or soft delete if we had is_active column logic in router update, but delete is cleaner for management
        res = supabase.table("api_keys").delete().eq("id", key_id).execute()
        return {"status": "success", "deleted": key_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/keys/{key_id}/reset")
async def reset_usage(key_id: str):
    """Reset usage for a key."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    try:
        supabase.table("api_keys").update({"usage_tokens": 0}).eq("id", key_id).execute()
        return {"status": "reset"}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))
