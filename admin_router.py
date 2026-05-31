from __future__ import annotations

import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from auth_cache import api_key_cache_status, refresh_api_key_cache
from cli_proxy import (
    PUBLIC_CLI_MODEL_ALIASES,
    cli_model_provider,
    get_active_cli_auth_providers,
    get_enabled_cli_models,
    set_enabled_cli_models,
    cli_management_request,
    enable_cli_auth_session,
    disable_cli_auth_session,
)
from db import get_supabase
from local_db import (
    create_api_key as local_create_api_key,
    delete_api_key as local_delete_api_key,
    list_api_keys as local_list_api_keys,
    lookup_api_key as local_lookup_api_key,
    reset_usage as local_reset_usage,
)

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


class SessionStatusRequest(BaseModel):
    id: str
    disabled: bool


@router.get("/keys", response_model=list[APIKey])
async def list_keys():
    supabase = get_supabase()
    if not supabase:
        return local_list_api_keys()
    try:
        res = supabase.table("kaiapi_api_keys").select("*").order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        return local_list_api_keys()


@router.post("/keys", response_model=APIKey)
async def create_key(req: CreateKeyRequest):
    supabase = get_supabase()
    new_key = {
        "name": req.name,
        "token": f"sk-kai-{secrets.token_urlsafe(16)}",
        "limit_tokens": req.limit_tokens,
        "usage_tokens": 0,
        "is_active": True,
    }

    if not supabase:
        key = local_create_api_key(req.name, req.limit_tokens)
        refresh_api_key_cache()
        return key

    try:
        res = supabase.table("kaiapi_api_keys").insert(new_key).execute()
        if res.data:
            refresh_api_key_cache()
            return res.data[0]
        raise HTTPException(status_code=500, detail="Failed to create key")
    except HTTPException:
        raise
    except Exception as e:
        key = local_create_api_key(req.name, req.limit_tokens)
        refresh_api_key_cache()
        return key


@router.delete("/keys/{key_id}")
async def revoke_key(key_id: str):
    supabase = get_supabase()
    if not supabase:
        local_delete_api_key(key_id)
        refresh_api_key_cache()
        return {"status": "success", "deleted": key_id, "source": "local"}
    try:
        supabase.table("kaiapi_api_keys").delete().eq("id", key_id).execute()
        refresh_api_key_cache()
        return {"status": "success", "deleted": key_id}
    except Exception as e:
        local_delete_api_key(key_id)
        refresh_api_key_cache()
        return {"status": "success", "deleted": key_id, "source": "local"}


@router.post("/keys/{key_id}/reset")
async def reset_usage(key_id: str):
    supabase = get_supabase()
    if not supabase:
        local_reset_usage(key_id)
        refresh_api_key_cache()
        return {"status": "reset", "source": "local"}
    try:
        supabase.table("kaiapi_api_keys").update({"usage_tokens": 0}).eq("id", key_id).execute()
        refresh_api_key_cache()
        return {"status": "reset"}
    except Exception as e:
        local_reset_usage(key_id)
        refresh_api_key_cache()
        return {"status": "reset", "source": "local"}


@router.post("/keys/lookup")
async def lookup_key_by_token(req: LookupKeyRequest):
    supabase = get_supabase()
    if not supabase:
        key = local_lookup_api_key(req.token)
        if not key:
            raise HTTPException(status_code=404, detail="Key not found")
        return {
            "name": key.get("name"),
            "usage_tokens": key.get("usage_tokens", 0),
            "limit_tokens": key.get("limit_tokens", 0),
            "remaining": key.get("limit_tokens", 0) - key.get("usage_tokens", 0),
            "created_at": key.get("created_at"),
            "is_active": key.get("is_active", True),
        }
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
        key = local_lookup_api_key(req.token)
        if not key:
            raise HTTPException(status_code=404, detail="Key not found")
        return {
            "name": key.get("name"),
            "usage_tokens": key.get("usage_tokens", 0),
            "limit_tokens": key.get("limit_tokens", 0),
            "remaining": key.get("limit_tokens", 0) - key.get("usage_tokens", 0),
            "created_at": key.get("created_at"),
            "is_active": key.get("is_active", True),
            "source": "local",
        }


@router.get("/models")
async def list_model_settings():
    enabled = set(get_enabled_cli_models())
    active_providers = await get_active_cli_auth_providers()
    return {
        "models": [
            {
                "id": model,
                "routes_to": target,
                "provider": cli_model_provider(model),
                "enabled": model in enabled,
            }
            for model, target in PUBLIC_CLI_MODEL_ALIASES.items()
            if cli_model_provider(model) in active_providers
        ],
        "enabled_models": [model for model in enabled if cli_model_provider(model) in active_providers],
        "active_providers": sorted(active_providers),
    }


@router.put("/models")
async def update_model_settings(req: ModelSelectionRequest):
    enabled = set_enabled_cli_models(req.enabled_models)
    return {"status": "ok", "enabled_models": enabled}


@router.get("/keys/cache")
async def get_key_cache_status():
    return api_key_cache_status()


@router.post("/keys/cache/refresh")
async def refresh_key_cache():
    try:
        return refresh_api_key_cache()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/sessions")
async def list_auth_sessions():
    """Proxy the auth-files management endpoint to list all connected sessions."""
    try:
        return await cli_management_request("GET", "auth-files")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/auth/sessions")
async def toggle_auth_session(req: SessionStatusRequest):
    """Toggle a specific CLI auth session enabled/disabled status."""
    if req.disabled:
        success = await disable_cli_auth_session(req.id)
    else:
        success = await enable_cli_auth_session(req.id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to toggle session status")
    return {"status": "ok", "id": req.id, "disabled": req.disabled}
