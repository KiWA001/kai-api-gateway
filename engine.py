"""
CLIProxy-only engine.

This keeps the Python runtime small for Hugging Face: all model execution goes
through the local CLIProxyAPI sidecar.
"""

from __future__ import annotations

import logging
import time

from config import MODEL_RANKING, SUPABASE_KEY, SUPABASE_URL
from models import ModelInfo
from providers.cli_proxy_provider import CLIProxyProvider
from cli_proxy import get_enabled_cli_models, get_runtime_enabled_cli_models

logger = logging.getLogger("kai_api.engine")


class AIEngine:
    def __init__(self):
        self._provider = CLIProxyProvider()
        self._stats: dict[str, dict] = {}
        self.supabase = None

        try:
            from supabase import create_client

            self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            self._load_stats()
        except Exception as e:
            logger.warning(f"Stats database unavailable: {e}")

    def _load_stats(self):
        if not self.supabase:
            return
        try:
            response = self.supabase.table("kaiapi_model_stats").select("*").execute()
            self._stats = {
                row["id"]: {
                    "success": row.get("success", 0),
                    "failure": row.get("failure", 0),
                    "consecutive_failures": row.get("consecutive_failures", 0),
                    "avg_time_ms": row.get("avg_time_ms", 0),
                    "total_time_ms": row.get("total_time_ms", 0),
                    "count_samples": row.get("count_samples", 0),
                }
                for row in response.data
            }
        except Exception as e:
            logger.warning(f"Failed to load stats: {e}")

    def _save_stat(self, model: str):
        if not self.supabase:
            return
        try:
            data = self._stats.get(model, {})
            self.supabase.table("kaiapi_model_stats").upsert(
                {
                    "id": model,
                    "success": data.get("success", 0),
                    "failure": data.get("failure", 0),
                    "consecutive_failures": data.get("consecutive_failures", 0),
                    "avg_time_ms": data.get("avg_time_ms", 0),
                    "total_time_ms": data.get("total_time_ms", 0),
                    "count_samples": data.get("count_samples", 0),
                }
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to save stats for {model}: {e}")

    def _record_success(self, model: str, elapsed_ms: float):
        stats = self._stats.setdefault(
            model,
            {
                "success": 0,
                "failure": 0,
                "consecutive_failures": 0,
                "avg_time_ms": 0,
                "total_time_ms": 0,
                "count_samples": 0,
            },
        )
        stats["success"] += 1
        stats["consecutive_failures"] = 0
        stats["total_time_ms"] += elapsed_ms
        stats["count_samples"] += 1
        stats["avg_time_ms"] = stats["total_time_ms"] / stats["count_samples"]
        self._save_stat(model)

    def _record_failure(self, model: str):
        stats = self._stats.setdefault(
            model,
            {
                "success": 0,
                "failure": 0,
                "consecutive_failures": 0,
                "avg_time_ms": 0,
                "total_time_ms": 0,
                "count_samples": 0,
            },
        )
        stats["failure"] += 1
        stats["consecutive_failures"] += 1
        self._save_stat(model)

    def get_provider(self, name: str):
        return self._provider if name == "cli" else None

    def get_all_providers(self):
        return {"cli": self._provider}

    def get_enabled_providers(self):
        return {"cli": self._provider}

    def get_all_models(self) -> list[ModelInfo]:
        return [ModelInfo(model=model, provider="cli") for model in get_enabled_cli_models()]

    def get_stats(self) -> dict:
        self._load_stats()
        return self._stats

    def clear_stats(self):
        self._stats = {}
        if self.supabase:
            try:
                self.supabase.table("kaiapi_model_stats").delete().neq("id", "0").execute()
            except Exception as e:
                logger.warning(f"Failed to clear stats: {e}")

    async def test_all_models(self) -> list[dict]:
        results = []
        for model in await get_runtime_enabled_cli_models():
            started = time.perf_counter()
            try:
                await self._provider.send_message("Hi", model=model)
                elapsed = (time.perf_counter() - started) * 1000
                self._record_success(model, elapsed)
                results.append({"id": model, "model": model, "status": "PASS", "time_ms": elapsed})
            except Exception as e:
                self._record_failure(model)
                results.append({"id": model, "model": model, "status": "FAIL", "error": str(e)[:160]})
        return results

    async def health_check_all(self) -> list[dict]:
        try:
            ok = await self._provider.health_check()
            return [{"provider": "cli", "status": "healthy" if ok else "unhealthy"}]
        except Exception as e:
            return [{"provider": "cli", "status": "unhealthy", "error": str(e)}]

    async def chat(
        self,
        prompt: str,
        model: str | None = None,
        provider: str = "auto",
        system_prompt: str | None = None,
    ) -> dict:
        enabled_models = await get_runtime_enabled_cli_models()
        if not enabled_models:
            raise ValueError("No ready OAuth models are available. Add or refresh an OAuth session in the admin page.")

        requested = None if model in {None, "", "auto"} else model
        if requested and requested not in enabled_models:
            raise ValueError(f"Model '{requested}' is disabled. Enable it in the admin model settings.")

        candidates = [requested] if requested else enabled_models
        errors = []
        for candidate in candidates:
            started = time.perf_counter()
            try:
                result = await self._provider.send_message(prompt, model=candidate, system_prompt=system_prompt)
                elapsed = (time.perf_counter() - started) * 1000
                self._record_success(candidate, elapsed)
                result["model"] = candidate
                result["provider"] = "cli"
                result["response_time_ms"] = elapsed
                result["attempts"] = len(errors) + 1
                return result
            except Exception as e:
                self._record_failure(candidate)
                errors.append(f"{candidate}: {e}")

        raise ValueError("All enabled CLI models failed: " + " | ".join(errors[-5:]))
