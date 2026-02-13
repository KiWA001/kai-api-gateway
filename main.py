"""
K-AI API — Main Application
---------------------------
Free AI proxy API. No signup, no API keys on the AI side.
Users send a message, get an AI response from the best available provider.

Run with:  uvicorn main:app --host 0.0.0.0 --port 8000
"""

import os
import sys

print("🔥 STARTING K-AI API... 🔥", file=sys.stderr)
print(f"Current Working Directory: {os.getcwd()}", file=sys.stderr)
print(f"Directory Contents: {os.listdir('.')}", file=sys.stderr)

# Fix for Vercel Read-Only File System
# Must be set BEFORE importing g4f or engine
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    os.environ["HOME"] = "/tmp"

import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html

from config import (
    API_TITLE,
    API_DESCRIPTION,
    API_VERSION,
    CORS_ORIGINS,
    CORS_METHODS,
    CORS_HEADERS,
)
from models import (
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    ModelsResponse,
    HealthResponse,
    ProviderHealth,
)
from models import (
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    ModelsResponse,
    HealthResponse,
    ProviderHealth,
)
from services import engine, search_engine
from v1_router import router as v1_router
from admin_router import router as admin_router

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("kai_api")

# ---------- App ----------
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    docs_url=None,  # Disable default docs to serve custom one
    redoc_url=None,
)

# Mount static files (for CSS/JS if needed later)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Error Handling (Global)
from error_handling import openai_error

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Override default 404/401/500 to return OpenAI-style JSON.
    """
    code = "invalid_request_error"
    if exc.status_code == 401: code = "invalid_api_key"
    if exc.status_code == 429: code = "insufficient_quota"
    if exc.status_code == 404: code = "model_not_found"
    if exc.status_code == 500: code = "internal_server_error"

    return openai_error(
        message=exc.detail,
        code=code,
        status_code=exc.status_code
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
)

# AI Engine (initialized via services.py)
# engine = AIEngine() -> Moved to services.py
# search_engine = SearchEngine() -> Moved to services.py

# Include OpenAI Router
app.include_router(v1_router)
app.include_router(admin_router)


# ---------- Admin Routes ----------
@app.get("/qazmlp", include_in_schema=False)
async def admin_page():
    """Serve the Secret Admin Dashboard."""
    return FileResponse("static/qaz.html")


@app.get("/qaz/stats", include_in_schema=False)
async def admin_stats():
    """Return raw model stats for dashboard."""
    return JSONResponse(engine.get_stats())


@app.post("/qaz/test_all", include_in_schema=False)
async def admin_test_all():
    """Trigger parallel testing of all models."""
    results = await engine.test_all_models()
    return JSONResponse(results)


@app.post("/qaz/clear_stats", include_in_schema=False)
async def admin_clear_stats():
    """Clear all stats."""
    engine.clear_stats()
    return JSONResponse({"status": "cleared"})


@app.get("/qaz/debug_g4f", include_in_schema=False)
async def admin_debug_g4f():
    """
    Verbose Debug for G4F Provider on Server.
    Captures logs to see which providers are failing.
    """
    import io
    import sys
    import logging
    from contextlib import redirect_stdout, redirect_stderr
    import g4f
    from g4f.client import AsyncClient
    from useragent import get_random_user_agent

    # Enable logging
    g4f.debug.logging = True
    
    # Capture output
    f = io.StringIO()
    
    # We must also redirect logging stream if possible, or just rely on stdout/stderr
    # g4f logs to stderr mostly
    
    with redirect_stdout(f), redirect_stderr(f):
        print("=== G4F DEBUG LOG ===")
        print(f"G4F Version: {g4f.version}")
        
        ua = get_random_user_agent()
        print(f"Testing with User-Agent: {ua[:30]}...")
        
        # We need to simulate the environment
        import os
        os.environ["HOME"] = "/tmp"
        
        # Test 1: GPT-4o-mini
        print("\n--- Testing gpt-4o-mini ---")
        try:
            client = AsyncClient(headers={"User-Agent": ua})
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hi"}],
            )
            print(f"✅ Success! Provider: {response.provider}")
            print(f"Response: {response.choices[0].message.content[:20]}...")
        except Exception as e:
            print(f"❌ Failed: {e}")

        # Test 2: GPT-4
        print("\n--- Testing gpt-4 ---")
        try:
            client = AsyncClient(headers={"User-Agent": ua})
            response = await client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": "Hi"}],
            )
            print(f"✅ Success! Provider: {response.provider}")
            print(f"Response: {response.choices[0].message.content[:20]}...")
        except Exception as e:
            print(f"❌ Failed: {e}")

    output = f.getvalue()
    return HTMLResponse(f"<pre>{output}</pre>")


# ---------- Custom Swagger UI ----------
# ---------- Custom Swagger UI ----------
@app.get("/docs", include_in_schema=False)
async def public_swagger_ui():
    """Serve Public Swagger UI (No Admin)."""
    return get_swagger_ui_html(
        openapi_url="/openapi_public.json",
        title=f"{API_TITLE} - Public Docs",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )

@app.get("/qazmlpdocs", include_in_schema=False)
async def admin_swagger_ui():
    """Serve Admin Swagger UI (Full)."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url, # Default includes Admin
        title=f"{API_TITLE} - Admin Docs",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )

@app.get("/openapi_public.json", include_in_schema=False)
async def get_public_openapi():
    """Generate OpenAPI schema without Admin routes."""
    if app.openapi_schema:
        schema = app.openapi_schema.copy()
    else:
        schema = app.openapi()
        
    # Deep copy to avoid modifying the cached schema
    import copy
    public_schema = copy.deepcopy(schema)
    
    # Filter paths
    paths_to_remove = []
    for path, methods in public_schema.get("paths", {}).items():
        # Check if any Method in this path has "Admin" tag
        is_admin = False
        for method, details in methods.items():
            if "tags" in details and "Admin" in details["tags"]:
                is_admin = True
                break
        
        if is_admin or path.startswith("/qaz") or path.startswith("/admin"):
            paths_to_remove.append(path)
            
    for p in paths_to_remove:
        del public_schema["paths"][p]
        
    return JSONResponse(public_schema)


# ---------- Search Routes ----------
@app.post("/search")
async def search_endpoint(request: Request):
    """
    Perform a standard web search.
    Body: {"query": "something", "limit": 10}
    """
    try:
        data = await request.json()
        query = data.get("query")
        limit = data.get("limit", 10)
        
        if not query:
            return JSONResponse({"error": "Query required"}, status_code=400)
            
        results = search_engine.simple_search(query, max_results=limit)
        return JSONResponse({"results": results})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/deep_research")
async def deep_research_endpoint(request: Request):
    """
    Perform Deep Research: Search -> Scrape -> Synthesize.
    Body: {"query": "complex topic"}
    """
    try:
        data = await request.json()
        query = data.get("query")
        
        if not query:
            return JSONResponse({"error": "Query required"}, status_code=400)
        
        # 1. Gather Content (Offload to thread)
        import asyncio
        loop = asyncio.get_event_loop()
        
        # Gather context (Search + Scrape)
        raw_context = await loop.run_in_executor(None, search_engine.deep_research_gather, query)
        
        if not raw_context:
             return JSONResponse({"report": "No relevant information found."})
        
        # 2. Return Raw Context (No AI Synthesis to avoid Hallucination)
        return JSONResponse({
            "report": "### Deep Research Results\n\n" + raw_context,
            "model": "scraper-v1", 
            "sources": "Derived from DuckDuckGo Search (Raw Content)"
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ---------- Routes ----------




@app.get("/docs/public", include_in_schema=False)
async def public_docs_page():
    """Serve the Stripped Public Documentation."""
    return FileResponse("static/public_docs.html")

@app.get("/", tags=["Dashboard"])
async def root():
    """Serve the HTML Dashboard."""
    return FileResponse("static/docs.html", headers={"X-API-Version": "2.0.1-NewAuth"})


@app.get(
    "/models",
    response_model=ModelsResponse,
    tags=["Models"],
)
async def list_models():
    """List all available AI models across all providers."""
    if not engine:
        return ModelsResponse(models=[], total=0)
        
    models = engine.get_all_models()
    return ModelsResponse(
        models=models,
        total=len(models),
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
)
async def health_check():
    """
    Run health checks on all providers.
    """
    if not engine:
        return HealthResponse(
            status="unhealthy",
            version="2.0.0",
            uptime=0, # TODO: Track uptime
            providers={},
            error="AI Engine failed to initialize (check logs)"
        )
        
    # Get provider health
    logger.info("Running health checks...")
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

    # Determine overall status
    healthy_count = sum(1 for p in providers if p.status == "healthy")
    if healthy_count == len(providers):
        overall = "healthy"
    elif healthy_count > 0:
        overall = "degraded"
    else:
        overall = "unhealthy"

    return HealthResponse(
        status=overall,
        providers=providers,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )
