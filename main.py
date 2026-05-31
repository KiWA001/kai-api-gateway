"""
K-AI API - CLIProxy OAuth gateway.
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from admin_router import router as admin_router
from auth_cache import refresh_api_key_cache
from cli_proxy import restore_cli_auth_files_from_supabase
from cli_proxy_router import router as cli_proxy_router
from config import API_DESCRIPTION, API_TITLE, API_VERSION, CORS_HEADERS, CORS_METHODS, CORS_ORIGINS
from error_handling import openai_error
from models import HealthResponse, ModelsResponse, ProviderHealth
from services import engine
from v1_router import router as v1_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("kai_api")

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    docs_url=None,
    redoc_url=None,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
)

app.include_router(v1_router)
app.include_router(cli_proxy_router)
app.include_router(admin_router)


@app.on_event("startup")
async def restore_oauth_sessions_on_startup():
    try:
        key_result = refresh_api_key_cache()
        logger.info("API key cache: %s", key_result)
    except Exception as exc:
        logger.warning("API key cache load failed: %s", exc)

    try:
        result = restore_cli_auth_files_from_supabase()
        logger.info("OAuth session restore: %s", result)
    except Exception as exc:
        logger.warning("OAuth session restore failed: %s", exc)


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException):
    code = "invalid_request_error"
    if exc.status_code == 401:
        code = "invalid_api_key"
    elif exc.status_code == 429:
        code = "insufficient_quota"
    elif exc.status_code == 404:
        code = "model_not_found"
    elif exc.status_code >= 500:
        code = "internal_server_error"

    return openai_error(message=exc.detail, code=code, status_code=exc.status_code)


@app.get("/qazmlp", include_in_schema=False)
async def admin_page():
    return FileResponse("static/qaz.html")


@app.get("/docs", include_in_schema=False)
async def public_swagger_ui():
    return get_swagger_ui_html(
        openapi_url="/openapi_public.json",
        title=f"{API_TITLE} - Public Docs",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )


@app.get("/qazmlpdocs", include_in_schema=False)
async def admin_swagger_ui():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{API_TITLE} - Admin Docs",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )


@app.get("/openapi_public.json", include_in_schema=False)
async def get_public_openapi():
    import copy

    schema = copy.deepcopy(app.openapi())
    for path in list(schema.get("paths", {})):
        if path.startswith("/qaz"):
            del schema["paths"][path]
    return JSONResponse(schema)


@app.get("/docs/public", include_in_schema=False)
async def public_docs_page():
    return FileResponse("static/public_docs.html")


@app.get("/", tags=["Dashboard"])
async def root():
    return FileResponse("static/docs.html", headers={"X-API-Version": API_VERSION})


@app.get("/models", response_model=ModelsResponse, tags=["Models"])
async def list_models():
    if not engine:
        return ModelsResponse(models=[], total=0)
    models = engine.get_all_models()
    return ModelsResponse(models=models, total=len(models))


@app.get("/qaz/stats", include_in_schema=False)
async def admin_stats():
    if not engine:
        return JSONResponse({})
    return JSONResponse(engine.get_stats())


@app.post("/qaz/test_all", include_in_schema=False)
async def admin_test_all():
    if not engine:
        raise HTTPException(status_code=503, detail="Engine unavailable")
    return JSONResponse(await engine.test_all_models())


@app.post("/qaz/clear_stats", include_in_schema=False)
async def admin_clear_stats():
    if engine:
        engine.clear_stats()
    return JSONResponse({"status": "cleared"})


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    if not engine:
        return HealthResponse(status="unhealthy", providers=[], timestamp=datetime.utcnow().isoformat() + "Z")

    results = await engine.health_check_all()
    providers = [
        ProviderHealth(
            provider=r["provider"],
            status=r["status"],
            response_time_ms=r.get("response_time_ms"),
            error=r.get("error"),
        )
        for r in results
    ]
    healthy_count = sum(1 for p in providers if p.status == "healthy")
    overall = "healthy" if healthy_count == len(providers) else "degraded" if healthy_count else "unhealthy"
    return HealthResponse(status=overall, providers=providers, timestamp=datetime.utcnow().isoformat() + "Z")
