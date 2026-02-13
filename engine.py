"""
AI Engine
---------
Model-ranked exhaustive fallback engine with PERSISTENT ADAPTIVE LEARNING via SUPABASE.

Instead of trying providers, this engine tries MODELS ranked by quality.
Each model is tried across all providers that support it.
Only after exhausting ALL model+provider combinations does it return an error.

The user doesn't care about wait time — reliability is everything.
"""

import logging
import time
import asyncio
from supabase import create_client, Client
from providers.base import BaseProvider
from providers.g4f_provider import G4FProvider
from providers.pollinations_provider import PollinationsProvider
from providers.gemini_provider import GeminiProvider
from providers.zai_provider import ZaiProvider
from config import MODEL_RANKING, PROVIDER_MODELS, SUPABASE_URL, SUPABASE_KEY
from models import ModelInfo
from sanitizer import sanitize_response

logger = logging.getLogger("kai_api.engine")


class AIEngine:
    """
    Model-ranked exhaustive fallback engine with ADAPTIVE LEARNING.

    On each request:
    1. If model specified, try it first.
    2. If no model, use ADAPTIVE RANKING (Success History + TIMING + Static Ranking).
       - Models that Worked Recently get promoted to top.
       - FAST models get promoted (Time Weighted Ranking).
       - Models that Failed get demoted heavily.
       - CIRCUIT BREAKER: If a model fails 3 times in a row, it gets a massive penalty.
       - Stats are synced to SUPABASE so knowledge persists across Vercel restarts.
    3. Exhaustively try all options before giving up.
    4. Each attempt creates a fresh session — fully stateless.
    5. Responses are sanitized.
    """

    def __init__(self):
        self._providers: dict[str, BaseProvider] = {
            "g4f": G4FProvider(),
            "pollinations": PollinationsProvider(),
        }
        # Z.ai requires Playwright + Chromium (not available on Vercel serverless)
        if ZaiProvider.is_available():
            self._providers["zai"] = ZaiProvider()
            logger.info("✅ Z.ai provider enabled (Playwright available)")
            
            # Gemini also uses Playwright, so we enable it here too
            self._providers["gemini"] = GeminiProvider()
            logger.info("✅ Gemini provider enabled")
        else:
            logger.warning("⚠️ Z.ai/Gemini providers disabled (Playwright not installed)")
        # Success Tracker: Key = "provider/model_id"
        # Value = {success, failure, consecutive_failures, avg_time_ms, total_time_ms, count_samples}
        self._stats: dict[str, dict] = {}
        
        # Connect to Supabase
        self.supabase = None
        try:
            self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            self._load_stats()
        except Exception as e:
            logger.error(f"Supabase connection failed: {e}")
            # We continue with empty stats (safe fallback)
            
        # Lookup map for Friendly Names: (provider, model_id) -> friendly_name
        self._friendly_lookup = {
            (p, m): f for f, p, m in MODEL_RANKING
        }
        
        # Validation Sets
        self._valid_providers = set(self._providers.keys())
        self._valid_friendly_models = {f for f, p, m in MODEL_RANKING}
        self._valid_provider_models = set()
        for p_name, p_instance in self._providers.items():
            for m in p_instance.get_available_models():
                self._valid_provider_models.add(m)
                self._valid_provider_models.add(f"{p_name}/{m}")

    def _load_stats(self):
        """Load persistent stats from Supabase."""
        if not self.supabase:
            return

        try:
            # Fetch all stats
            response = self.supabase.table("model_stats").select("*").execute()
            for row in response.data:
                self._stats[row['id']] = {
                    "success": row.get('success', 0),
                    "failure": row.get('failure', 0),
                    "consecutive_failures": row.get('consecutive_failures', 0),
                    "avg_time_ms": row.get('avg_time_ms', 0),
                    "total_time_ms": row.get('total_time_ms', 0),
                    "count_samples": row.get('count_samples', 0)
                }
            logger.info(f"Loaded stats for {len(self._stats)} models from Supabase")
        except Exception as e:
            logger.error(f"Failed to load stats from Supabase: {e}")

    def _save_stat(self, key: str):
        """Sync a single model's stats to Supabase (Upsert)."""
        if not self.supabase:
            return

        try:
            data = self._stats.get(key, {})
            record = {
                "id": key,
                "success": data.get("success", 0),
                "failure": data.get("failure", 0),
                "consecutive_failures": data.get("consecutive_failures", 0),
                "avg_time_ms": data.get("avg_time_ms", 0),
                "total_time_ms": data.get("total_time_ms", 0),
                "count_samples": data.get("count_samples", 0)
            }
            self.supabase.table("model_stats").upsert(record).execute()
        except Exception as e:
            logger.error(f"Failed to save stats for {key}: {e}")

    def get_provider(self, name: str) -> BaseProvider | None:
        return self._providers.get(name)

    def get_all_providers(self) -> dict[str, BaseProvider]:
        return self._providers

    def get_all_models(self) -> list[ModelInfo]:
        models = []
        for provider in self._providers.values():
            for model_name in provider.get_available_models():
                models.append(
                    ModelInfo(model=model_name, provider=provider.name)
                )
        return models

    def _get_score(self, key: str) -> float:
        """
        Calculate TIME-WEIGHTED SCORE.
        
        Formula:
        Base Score = Success - (Failure * 2)
        Time Penalty = Average Time (seconds)
        Final Score = Base Score - Time Penalty
        
        Examples:
        - 100% Success, 0.5s avg: 100 - 0.5 = 99.5
        - 100% Success, 5.0s avg: 100 - 5.0 = 95.0
        -> Fast models rank higher.
        
        Circuit Breaker: >=5 consecutive failures = -500.0 penalty.
        """
        data = self._stats.get(key, {})
        success = data.get("success", 0)
        failure = data.get("failure", 0)
        consecutive = data.get("consecutive_failures", 0)
        avg_time_ms = data.get("avg_time_ms", 0)
        
        # Base Score (Failures are punished 2x)
        base_score = success - (failure * 2)
        
        # Time Penalty (Time in seconds)
        # e.g. 500ms = 0.5 penalty
        # e.g. 2000ms = 2.0 penalty
        time_penalty = avg_time_ms / 1000.0
        
        final_score = base_score - time_penalty
        
        # CIRCUIT BREAKER: 5 strikes -> Moderate penalty, not death.
        # This allows it to recover if others fail too.
        if consecutive >= 5:
            return final_score - 500.0
            
        return final_score

    def _record_success(self, provider: str, model_id: str, elapsed_ms: float = 0):
        """Boost score: Increment success, update time stats, reset consecutive failures."""
        # Use friendly name if available, else provider/model
        key = self._friendly_lookup.get((provider, model_id), f"{provider}/{model_id}")
        
        if key not in self._stats:
            self._stats[key] = {
                "success": 0, "failure": 0, "consecutive_failures": 0,
                "avg_time_ms": 1000, "total_time_ms": 0, "count_samples": 0
            }
        
        stats = self._stats[key]
        stats["success"] += 1
        stats["consecutive_failures"] = 0  # Reset penalty
        
        # Update Time Stats
        if elapsed_ms > 0:
            stats["total_time_ms"] += elapsed_ms
            stats["count_samples"] += 1
            stats["avg_time_ms"] = stats["total_time_ms"] / stats["count_samples"]
        
        score = self._get_score(key)
        logger.info(f"📈 Success! {key} ({elapsed_ms}ms). New Score: {score:.2f} (Avg: {stats['avg_time_ms']:.0f}ms)")
        
        # Persist to Supabase
        self._save_stat(key)

    def _record_failure(self, provider: str, model_id: str):
        """Punish score: Increment failure count AND consecutive failures."""
        # Use friendly name if available, else provider/model
        key = self._friendly_lookup.get((provider, model_id), f"{provider}/{model_id}")
        
        if key not in self._stats:
            self._stats[key] = {
                "success": 0, "failure": 0, "consecutive_failures": 0,
                "avg_time_ms": 1000, "total_time_ms": 0, "count_samples": 0
            }
            
        self._stats[key]["failure"] += 1
        self._stats[key]["consecutive_failures"] = self._stats[key].get("consecutive_failures", 0) + 1
        
        score = self._get_score(key)
        cf = self._stats[key]["consecutive_failures"]
        
        if cf >= 5:
            logger.warning(f"📉 CIRCUIT BREAKER ACTIVATED for {key}! CF:{cf}. Score: {score:.2f}")
        else:
            logger.info(f"📉 Failure! {key} score: {score:.2f} (CF:{cf})")
            
        # Persist to Supabase
        self._save_stat(key)

    def _get_sorted_ranking(self) -> list[tuple[str, str, str]]:
        """
        Return MODEL_RANKING sorted by Time-Weighted Score (descending).
        """
        return sorted(
            MODEL_RANKING,
            key=lambda x: self._get_score(f"{x[1]}/{x[2]}"),
            reverse=True
        )

    def get_stats(self) -> dict:
        """
        Return raw stats for Admin Dashboard.
        Refresh from Supabase first to ensure we see updates from other workers/lambdas.
        """
        if self.supabase:
            try:
                # Optimized: In a real high-traffic app we might cache this, 
                # but for this user, accurate immediate feedback is priority.
                self._load_stats()
            except Exception:
                pass
        return self._stats

    def clear_stats(self):
        """Clear all stats from memory AND Supabase."""
        self._stats = {}
        if self.supabase:
            try:
                # Delete all rows
                self.supabase.table("model_stats").delete().neq("id", "0").execute()
                logger.info("Cleared all stats from Supabase")
            except Exception as e:
                logger.error(f"Failed to clear Supabase stats: {e}")

    async def test_all_models(self) -> list[dict]:
        """
        Run a parallel liveness test on ALL models.
        Returns a list of results (success/fail) for the dashboard.
        """
        results = []
        
        # Helper for a single test
        async def test_one(friendly_name, prov_name, prov_model_id):
            key = f"{prov_name}/{prov_model_id}"
            combo = f"{prov_name}/{friendly_name}"
            prov = self.get_provider(prov_name)
            
            if not prov:
                return {
                    "id": key,
                    "model": friendly_name,
                    "status": "SKIP",
                    "error": "Provider missing"
                }
            
            try:
                # Simple "Hello" test
                # We do NOT record stats here to avoid polluting longterm data with short tests?
                # Actually user wants to see progress, maybe we SHOULD record it?
                # The user says "Test all AI"... implying a check.
                # Let's record it so the dashboard updates LIVE.
                res = await self._try_provider(prov, "Hi", prov_model_id, None)
                
                # Success - Record it
                self._record_success(prov_name, prov_model_id, res["response_time_ms"])
                
                return {
                    "id": key,
                    "model": friendly_name, 
                    "status": "PASS",
                    "time_ms": res["response_time_ms"]
                }
            except Exception as e:
                # Failure - Record it
                self._record_failure(prov_name, prov_model_id)
                return {
                    "id": key,
                    "model": friendly_name,
                    "status": "FAIL",
                    "error": str(e)[:100]
                }

        # Create tasks for all models in ranking
        tasks = []
        for fn, pn, pid in MODEL_RANKING:
            tasks.append(test_one(fn, pn, pid))
            
        # Run parallel
        results = await asyncio.gather(*tasks)
        return results

    async def chat(
        self,
        prompt: str,
        model: str | None = None,
        provider: str = "auto",
        system_prompt: str | None = None,
    ) -> dict:
        """
        Send a chat message with adaptive fallback.
        """

        # Strict Validation
        if model == "auto":
            model = None

        if provider != "auto" and provider not in self._valid_providers:
            raise ValueError(f"Unknown provider '{provider}'. Available: {list(self._valid_providers)}")
            
        if model:
            # Check if model is a known friendly name OR a valid provider model ID
            is_valid = (model in self._valid_friendly_models) or (model in self._valid_provider_models)
            if not is_valid:
                # Also check strict provider/model combos if provider is set
                if provider != "auto":
                     if not any(m == model for m in self._providers[provider].get_available_models()):
                         raise ValueError(f"Model '{model}' not found on provider '{provider}'")
                else:
                    raise ValueError(f"Unknown model '{model}'. check /models for list.")

        # Case 1: Specific provider requested
        if provider != "auto":
            p = self.get_provider(provider)
            # We already validated p exists above
            
            if model:
                # STRICT MODE: Specific Provider + Specific Model
                
                # Verify compatibility:
                # 1. Is it a friendly name supported by this provider?
                # 2. Is it a raw model ID supported by this provider?
                is_supported = False
                
                # Check friendly names in config
                for fn, pn, pid in MODEL_RANKING:
                    if fn == model and pn == provider:
                        is_supported = True
                        break
                
                # Check raw IDs
                if not is_supported:
                    if model in p.get_available_models():
                        is_supported = True
                        
                if not is_supported:
                    raise ValueError(f"Model '{model}' is not supported by provider '{provider}'")

                # Try ONLY this combination. If fail -> Error.
                result = await self._try_single(p, prompt, model, system_prompt)
                if result:
                    self._record_success(provider, model, result.get("response_time_ms", 0))
                    result["attempts"] = 1
                    return result
                
                self._record_failure(provider, model)
                raise ValueError(f"Strict Mode: Model '{model}' failed on provider '{provider}'")
                
            # STRICT MODE: Specific Provider + Any Model
            # Walk this provider's models (sorted by score for this provider)
            provider_entries = [
                (fn, pn, pid)
                for fn, pn, pid in MODEL_RANKING
                if pn == provider
            ]
            provider_entries.sort(
                key=lambda x: self._get_score(f"{x[1]}/{x[2]}"),
                reverse=True
            )

            for attempt, (fn, pn, pid) in enumerate(provider_entries, 1):
                try:
                    result = await self._try_provider(p, prompt, pid, system_prompt)
                    # Pass elapsed time
                    self._record_success(pn, pid, result["response_time_ms"])
                    result["model"] = fn
                    result["attempts"] = attempt
                    return result
                except Exception as e:
                    self._record_failure(pn, pid)
                    logger.warning(f"❌ {provider}/{fn}: {e}")

            # If we get here, all models on this provider failed.
            raise ValueError(f"Strict Mode: All models failed on provider '{provider}'")

        # Case 2: Specific model, any provider
        if model:
            attempts = []
            errors = []
            # Try to find which providers support this friendly model
            # OR if it's a raw model ID, try on all that support it
            
            # 1. Identify candidates (provider, model_id)
            candidates = []
            
            # Is it a friendly name?
            for fn, pn, pid in MODEL_RANKING:
                if fn == model:
                    candidates.append((pn, pid))
            
            # If no friendly match, maybe it's a direct ID?
            if not candidates:
                 for prov_name, prov in self._providers.items():
                     if model in prov.get_available_models():
                         candidates.append((prov_name, model))
            
            if not candidates:
                 raise ValueError(f"Model '{model}' not found in configuration.")

            # Sort candidates by score?
            candidates.sort(key=lambda x: self._get_score(f"{x[0]}/{x[1]}"), reverse=True)

            for prov_name, prov_model_id in candidates:
                prov = self._providers[prov_name]
                try:
                    result = await self._try_provider(prov, prompt, prov_model_id, system_prompt)
                    if result:
                         self._record_success(prov_name, prov_model_id, result.get("response_time_ms", 0))
                         result["attempts"] = len(attempts) + 1
                         # Ensure friendly name is returned if possible
                         friendly = self._friendly_lookup.get((prov_name, prov_model_id), model)
                         result["model"] = friendly 
                         return result
                except Exception as e:
                     self._record_failure(prov_name, prov_model_id)
                     errors.append(f"{prov_name}: {str(e)}")
                
                attempts.append(f"{prov_name}/{prov_model_id}")

            raise ValueError(f"Strict Mode: Model '{model}' failed on available providers: {errors}")

        # Case 3: Global Adaptive Fallback
        # Use the PERSISTENTLY SORTED ranking
        adaptive_ranking = self._get_sorted_ranking()
        
        # === "FALLEN GIANT" EXPLORATION (10% Chance) ===
        # Goal: Give "Better" models a "Fair Chance" if they are currently failing.
        # But ONLY if they are not the current #1.
        import random
        if len(adaptive_ranking) > 1 and random.random() < 0.1:
            # 1. Identify "Tier 1" models (The Giants)
            # These are the first 5 models in the static configuration.
            # We assume the config is ordered by "Intrinsic Quality".
            tier1_models = MODEL_RANKING[:5]
            tier1_keys = {f"{m[1]}/{m[2]}" for m in tier1_models}
            
            # 2. Find a Giant that has fallen (is not in the top 3 of current ranking)
            # logic: If a Tier 1 model is currently ranked > index 2, pick it.
            fallen_giants = []
            for idx, candidate in enumerate(adaptive_ranking):
                if idx < 3: continue  # Already at top, no need to boost
                
                c_key = f"{candidate[1]}/{candidate[2]}"
                if c_key in tier1_keys:
                    fallen_giants.append(candidate)
            
            if fallen_giants:
                # 3. Pick one to redeem
                contender = random.choice(fallen_giants)
                c_key = f"{contender[1]}/{contender[2]}"
                
                # Double check it's not "dead" (Circuit Breaker maxed out)?
                # Actually, the user WANTS to give them a fair chance.
                # So we let it run even if it has failures, as long as it's not completely banned?
                # The _try_provider loop will catch exceptions anyway.
                
                logger.info(f"🎲 FALLEN GIANT: Giving '{c_key}' a Fair Chance! (Promoting to #1)")
                
                # Move contender to the front
                adaptive_ranking.remove(contender)
                adaptive_ranking.insert(0, contender)
        # ===============================================
        
        errors = []
        attempt_count = 0

        for friendly_name, prov_name, prov_model_id in adaptive_ranking:
            prov = self.get_provider(prov_name)
            if not prov:
                continue

            attempt_count += 1
            combo = f"{prov_name}/{friendly_name}"
            
            try:
                # Log only if it's not the very first try (reduce noise)
                if attempt_count > 1:
                    logger.info(f"Attempt {attempt_count}: Trying {combo}")
                
                result = await self._try_provider(
                    prov, prompt, prov_model_id, system_prompt
                )
                
                # Success! Boost this model & Track Time
                self._record_success(prov_name, prov_model_id, result["response_time_ms"])
                
                result["model"] = friendly_name
                result["attempts"] = attempt_count
                return result

            except Exception as e:
                # Failure! Punish this model
                self._record_failure(prov_name, prov_model_id)
                
                error_msg = f"[{attempt_count}] {combo}: {e}"
                errors.append(error_msg)

        # ALL combinations failed
        total = len(errors)
        
        # AUTO-RECOVERY: If everything failed, the database might be full of "soft" bans.
        # Let's reset the consecutive failures so the next request gets a fresh start.
        logger.error("🚨 ALL MODELS FAILED! Triggering emergency stat reset for next run.")
        # We can't await here easily if we want to return fast, but we should try.
        # Actually, self.clear_stats() is synchronous in the sense it fires a request but...
        # Let's just do a fire-and-forget or simple reset if possible.
        # We will use the existing reset_stats logic but implemented inside.
        try:
             # Resetting memory stats immediately
             for k in self._stats:
                 self._stats[k]["consecutive_failures"] = 0
             
             # Attempt to reset Supabase (blocking, but necessary for persistence)
             if self.supabase:
                 self.supabase.table("model_stats").update({"consecutive_failures": 0}).gt("consecutive_failures", 0).execute()
        except Exception as reset_err:
             logger.error(f"Failed to auto-reset stats: {reset_err}")

        raise RuntimeError(
            f"All {total} model+provider combinations failed. "
            f"Stats have been auto-reset for the next attempt.\nLast errors:\n" + 
            "\n".join(errors[-5:])
        )

    async def _try_single(
        self,
        provider: BaseProvider,
        prompt: str,
        model: str | None,
        system_prompt: str | None,
    ) -> dict | None:
        """Try a single provider, return result or None on failure."""
        try:
            return await self._try_provider(
                provider, prompt, model, system_prompt
            )
        except Exception as e:
            # Failure is recorded by caller
            return None

    async def _try_provider(
        self,
        provider: BaseProvider,
        prompt: str,
        model: str | None,
        system_prompt: str | None,
    ) -> dict:
        """Try a single provider, sanitize the response, return with metadata."""
        start = time.time()

        result = await provider.send_message(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
        )

        # Calculate exact elapsed time in milliseconds
        elapsed_ms = (time.time() - start) * 1000

        # Sanitize the response — strip promotional spam, keep markdown
        clean_response = sanitize_response(result["response"])

        # If sanitization left an empty response, treat as failure
        if not clean_response:
            raise ValueError(
                f"Response from {provider.name} was empty after sanitization"
            )

        return {
            "response": clean_response,
            "model": result["model"],
            "provider": provider.name,
            "response_time_ms": elapsed_ms,
        }

    async def health_check_all(self) -> list[dict]:
        """Run health checks on all providers."""
        results = []
        for name, provider in self._providers.items():
            start = time.time()
            try:
                healthy = await provider.health_check()
                elapsed_ms = (time.time() - start) * 1000
                results.append({
                    "provider": name,
                    "status": "healthy" if healthy else "unhealthy",
                    "response_time_ms": elapsed_ms,
                    "error": None,
                })
            except Exception as e:
                elapsed_ms = (time.time() - start) * 1000
                results.append({
                    "provider": name,
                    "status": "unhealthy",
                    "response_time_ms": elapsed_ms,
                    "error": str(e),
                })
        return results
