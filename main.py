"""
K-AI API — Main Application
---------------------------
Free AI proxy API. No signup, no API keys on the AI side.
Users send a message, get an AI response from the best available provider.

Run with:  uvicorn main:app --host 0.0.0.0 --port 8000
"""

import os

# Fix for Vercel Read-Only File System
# Must be set BEFORE importing g4f or engine
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or True:
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
    return FileResponse("static/admin.html")


@app.get("/admin/stats", include_in_schema=False)
async def admin_stats():
    """Return raw model stats for dashboard."""
    return JSONResponse(engine.get_stats())


@app.post("/admin/test_all", include_in_schema=False)
async def admin_test_all():
    """Trigger parallel testing of all models."""
    results = await engine.test_all_models()
    return JSONResponse(results)


@app.post("/admin/clear_stats", include_in_schema=False)
async def admin_clear_stats():
    """Clear all stats."""
    engine.clear_stats()
    return JSONResponse({"status": "cleared"})


@app.get("/admin/debug_g4f", include_in_schema=False)
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
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Serve custom dark-themed Swagger UI."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{API_TITLE} - Swagger UI",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )


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


@app.get("/", tags=["Dashboard"])
async def root():
    """Serve the HTML Dashboard."""
    return FileResponse("static/docs.html")


@app.post(
    "/chat",
    response_model=ChatResponse,
    responses={500: {"model": ErrorResponse}},
    tags=["Chat"],
)
async def chat(request: ChatRequest):
    """
    Send a message and get an AI response.

    - **message**: Your prompt/question (required)
    - **model**: Optional model name (defaults to best available)
    - **provider**: "auto" (tries all), "g4f", or "pollinations"
    - **system_prompt**: Optional system instructions for the AI

    Each request is fully stateless — no conversation history has to be retained.
    If a specific provider is chosen, tries all models on that provider
    ranked by quality before falling back to other providers.
    All users have unlimited access — no rate limiting.
    """
    logger.info(
        f"Chat request: model={request.model}, provider={request.provider}, "
        f"message_length={len(request.message)}"
    )

    try:
        result = await engine.chat(
            prompt=request.message,
            model=request.model,
            provider=request.provider or "auto",
            system_prompt=request.system_prompt,
        )

        return ChatResponse(
            response=result["response"],
            model=result["model"],
            provider=result["provider"],
            attempts=result.get("attempts", 1),
            response_time_ms=result.get("response_time_ms"),
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"All models exhausted: {e}")
        raise HTTPException(
            status_code=503,
            detail=(
                "All AI models are currently unavailable. "
                "Please contact the developer to fix this issue. "
                f"Details: {str(e)}"
            ),
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
        )


@app.get(
    "/models",
    response_model=ModelsResponse,
    tags=["Models"],
)
async def list_models():
    """List all available AI models across all providers."""
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

    Returns the status of each provider and overall system health.
    """
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
