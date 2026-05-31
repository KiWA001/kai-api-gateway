from __future__ import annotations

import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cli_proxy import (
    PUBLIC_CLI_MODEL_ALIASES,
    get_enabled_cli_models,
    set_enabled_cli_models,
)
from db import get_supabase

router = APIRouter(prefix="/qaz", tags=["Admin"])


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


class LookupKeyRequest(BaseModel):
    token: str


class ModelSelectionRequest(BaseModel):
    enabled_models: list[str]


@router.get("/keys", response_model=list[APIKey])
async def list_keys():
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        res = supabase.table("kaiapi_api_keys").select("*").order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/keys", response_model=APIKey)
async def create_key(req: CreateKeyRequest):
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")

    new_key = {
        "name": req.name,
        "token": f"sk-kai-{secrets.token_urlsafe(16)}",
        "limit_tokens": req.limit_tokens,
        "usage_tokens": 0,
        "is_active": True,
    }

    try:
        res = supabase.table("kaiapi_api_keys").insert(new_key).execute()
        if res.data:
            return res.data[0]
        raise HTTPException(status_code=500, detail="Failed to create key")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/keys/{key_id}")
async def revoke_key(key_id: str):
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        supabase.table("kaiapi_api_keys").delete().eq("id", key_id).execute()
        return {"status": "success", "deleted": key_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/keys/{key_id}/reset")
async def reset_usage(key_id: str):
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        supabase.table("kaiapi_api_keys").update({"usage_tokens": 0}).eq("id", key_id).execute()
        return {"status": "reset"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/keys/lookup")
async def lookup_key_by_token(req: LookupKeyRequest):
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")
    if not req.token or not req.token.startswith("sk-"):
        raise HTTPException(status_code=400, detail="Invalid token format")

    try:
        res = supabase.table("kaiapi_api_keys").select("*").eq("token", req.token).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Key not found")
        key = res.data[0]
        return {
            "name": key.get("name"),
            "usage_tokens": key.get("usage_tokens", 0),
            "limit_tokens": key.get("limit_tokens", 0),
            "remaining": key.get("limit_tokens", 0) - key.get("usage_tokens", 0),
            "created_at": key.get("created_at"),
            "is_active": key.get("is_active", True),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_model_settings():
    enabled = set(get_enabled_cli_models())
    return {
        "models": [
            {
                "id": model,
                "routes_to": target,
                "provider": target.split("/", 1)[0],
                "enabled": model in enabled,
            }
            for model, target in PUBLIC_CLI_MODEL_ALIASES.items()
        ],
        "enabled_models": list(enabled),
    }


@router.put("/models")
async def update_model_settings(req: ModelSelectionRequest):
    enabled = set_enabled_cli_models(req.enabled_models)
    return {"status": "ok", "enabled_models": enabled}
