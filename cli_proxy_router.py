from __future__ import annotations

import os
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from auth import verify_api_key
from cli_proxy import (
    AUTH_PROVIDERS,
    CLI_PROXY_ENABLED,
    PUBLIC_CLI_MODEL_ALIASES,
    canonical_auth_provider,
    cli_api_request,
    cli_management_request,
    get_enabled_cli_models,
    is_cli_model_enabled,
)


router = APIRouter(prefix="/cli", tags=["CLI Proxy"])


class OAuthCallbackRequest(BaseModel):
    redirect_url: str = Field(
        ...,
        description="Full redirect URL copied after provider login.",
    )


@router.get("/auth/providers")
async def list_cli_auth_providers(_: dict = Depends(verify_api_key)):
    return {
        "enabled": CLI_PROXY_ENABLED,
        "providers": [
            {
                "id": provider_id,
                "label": meta["label"],
                "start_endpoint": f"/cli/auth/{provider_id}/start",
                "callback_endpoint": f"/cli/auth/{provider_id}/callback",
            }
            for provider_id, meta in AUTH_PROVIDERS.items()
        ],
    }


@router.post("/auth/{provider}/start")
async def start_cli_auth(provider: str, _: dict = Depends(verify_api_key)):
    try:
        provider_id = canonical_auth_provider(provider)
        if provider_id == "antigravity" and (
            not os.getenv("ANTIGRAVITY_OAUTH_CLIENT_ID", "").strip()
            or not os.getenv("ANTIGRAVITY_OAUTH_CLIENT_SECRET", "").strip()
        ):
            raise HTTPException(
                status_code=500,
                detail="Anti-Gravity OAuth is missing ANTIGRAVITY_OAUTH_CLIENT_ID or ANTIGRAVITY_OAUTH_CLIENT_SECRET on the server.",
            )
        if provider_id == "gemini" and (
            not os.getenv("GEMINI_OAUTH_CLIENT_ID", "").strip()
            or not os.getenv("GEMINI_OAUTH_CLIENT_SECRET", "").strip()
        ):
            raise HTTPException(
                status_code=500,
                detail="Gemini CLI OAuth is missing GEMINI_OAUTH_CLIENT_ID or GEMINI_OAUTH_CLIENT_SECRET on the server.",
            )
        meta = AUTH_PROVIDERS[provider_id]
        payload = await cli_management_request(
            "GET",
            meta["management_endpoint"],
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"CLI proxy auth start failed: {exc}") from exc

    auth_url = payload.get("url")
    state = payload.get("state")
    if not auth_url or not state:
        raise HTTPException(status_code=502, detail="CLI proxy did not return an auth URL")

    return {
        "status": "copy_url",
        "provider": provider_id,
        "label": meta["label"],
        "url": auth_url,
        "state": state,
        "instructions": f"Open this URL, finish login, then paste the final redirect URL into /cli/auth/{provider_id}/callback.",
    }


@router.post("/auth/{provider}/callback")
async def submit_cli_auth_callback(
    provider: str,
    request: OAuthCallbackRequest,
    _: dict = Depends(verify_api_key),
):
    try:
        provider_id = canonical_auth_provider(provider)
        meta = AUTH_PROVIDERS[provider_id]
        payload = await cli_management_request(
            "POST",
            "oauth-callback",
            json_body={
                "provider": meta["callback_provider"],
                "redirect_url": request.redirect_url,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"CLI proxy callback failed: {exc}") from exc

    return {"status": "submitted", "provider": provider_id, "result": payload}


@router.get("/auth/{provider}/status")
async def get_cli_auth_status(
    provider: str,
    state: str,
    _: dict = Depends(verify_api_key),
):
    try:
        provider_id = canonical_auth_provider(provider)
        payload = await cli_management_request(
            "GET",
            "get-auth-status",
            params={"state": state},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"CLI proxy status failed: {exc}") from exc

    return {"provider": provider_id, **payload}


@router.get("/auth/files")
async def list_cli_auth_files(_: dict = Depends(verify_api_key)):
    try:
        return await cli_management_request("GET", "auth-files")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"CLI proxy auth file list failed: {exc}") from exc


@router.get("/models")
async def list_cli_models(_: dict = Depends(verify_api_key)):
    enabled_models = set(get_enabled_cli_models())
    aliases = [
        {
            "id": alias,
            "provider": "cli",
            "display_name": alias,
            "routes_to": target,
            "type": "alias",
            "enabled": alias in enabled_models,
        }
        for alias, target in PUBLIC_CLI_MODEL_ALIASES.items()
        if alias in enabled_models
    ]

    try:
        response = await cli_api_request("GET", "v1/models")
        if response.status_code < 400:
            return {
                "status": "ok",
                "source": "sidecar",
                "aliases": aliases,
                "models": aliases,
            }
    except Exception:
        pass

    return {
        "status": "ok",
        "source": "static",
        "aliases": aliases,
        "models": aliases,
    }


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_cli_request(path: str, request: Request, _: dict = Depends(verify_api_key)):
    body = await request.body()
    if path.lstrip("/") in {"v1/chat/completions", "chat/completions"} and body:
        try:
            payload = json.loads(body.decode("utf-8"))
            if not is_cli_model_enabled(payload.get("model")):
                raise HTTPException(status_code=403, detail=f"Model '{payload.get('model')}' is disabled.")
        except HTTPException:
            raise
        except Exception:
            pass
    try:
        upstream = await cli_api_request(
            request.method,
            path,
            params=dict(request.query_params),
            content=body if body else None,
            headers=dict(request.headers),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"CLI proxy request failed: {exc}") from exc

    content_type = upstream.headers.get("content-type", "application/json")
    if content_type.startswith("application/json"):
        try:
            return JSONResponse(upstream.json(), status_code=upstream.status_code)
        except Exception:
            pass

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=content_type,
    )
