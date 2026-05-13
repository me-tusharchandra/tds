import asyncio
import logging
from urllib.parse import urlparse

from app.config import get_settings
from app.services import (
    competitor_discovery,
    exa_search,
    gemini_search,
    openai_search,
    perplexity_search,
    prompt_generator,
    scoring,
)
from app.services.brand_extractor import extract_brand_mentions
from app.services.citation_parser import SearchResult
from app.services.cost_tracker import CostTracker
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

MAX_COMPETITORS = 10

ENGINE_MODULES = {
    "openai": openai_search,
    "gemini": gemini_search,
    "perplexity": perplexity_search,
    "exa": exa_search,
}


def _active_engines(settings) -> dict:
    """Engines that have a usable credential for this run.

    Avoids spawning per-prompt tasks for engines we already know will skip.
    """
    has_or = bool(settings.openrouter_api_key)
    active: dict = {}
    if has_or or settings.openai_api_key:
        active["openai"] = openai_search
    if has_or or settings.gemini_api_key:
        active["gemini"] = gemini_search
    if has_or:
        active["perplexity"] = perplexity_search
    if settings.exa_api_key:
        active["exa"] = exa_search
    return active

# Throttle: write engine progress to DB every N completions
_ENGINE_PROGRESS_WRITE_INTERVAL = 4


def _extract_domain(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    return domain.lower().removeprefix("www.")


def _match_citation_to_competitor(
    cited_url: str, competitors: list[dict]
) -> str | None:
    """Match a citation URL to a competitor by domain."""
    cited_domain = _extract_domain(cited_url)
    for comp in competitors:
        comp_domain = comp.get("domain", "")
        if comp_domain and (
            cited_domain == comp_domain
            or cited_domain.endswith("." + comp_domain)
            or comp_domain.endswith("." + cited_domain)
        ):
            return comp["id"]
    return None


def _update_progress(db, analysis_id: str, progress: dict, status: str | None = None):
    """Write progress JSON (and optionally status) to the analyses row."""
    update = {"progress": progress}
    if status:
        update["status"] = status
    db.table("analyses").update(update).eq("id", analysis_id).execute()


async def run_analysis(analysis_id: str, brand_url: str) -> None:
    """Run the full analysis pipeline for a brand URL."""
    db = get_supabase()
    settings = get_settings()
    costs = CostTracker()
    progress: dict = {}

    try:
        # ── Status: discovering ──────────────────────────────────────
        _update_progress(db, analysis_id, progress, status="discovering")

        # Step 1: Discover competitors
        logger.info(f"[{analysis_id}] Discovering competitors for {brand_url}")
        discovery = await competitor_discovery.discover_competitors(
            brand_url, cost_tracker=costs
        )
        brand_info = discovery["brand_info"]

        # Insert brand as primary competitor
        brand_comp = (
            db.table("competitors")
            .insert(
                {
                    "analysis_id": analysis_id,
                    "name": brand_info["name"],
                    "url": brand_info["url"],
                    "domain": brand_info["domain"],
                    "description": brand_info.get("description", ""),
                    "is_primary": True,
                }
            )
            .execute()
        )
        all_competitors = [brand_comp.data[0]]

        # Insert discovered competitors (cap at MAX_COMPETITORS)
        discovered = discovery["competitors"][:MAX_COMPETITORS]
        for comp in discovered:
            result = (
                db.table("competitors")
                .insert(
                    {
                        "analysis_id": analysis_id,
                        "name": comp["name"],
                        "url": comp["url"],
                        "domain": comp["domain"],
                        "description": comp.get("description", ""),
                        "is_primary": False,
                    }
                )
                .execute()
            )
            all_competitors.append(result.data[0])

        progress["competitors_found"] = len(discovered)
        logger.info(f"[{analysis_id}] Found {len(discovered)} competitors")

        # ── Status: generating_prompts ───────────────────────────────
        db.table("analyses").update(
            {"brand_name": brand_info["name"], "brand_domain": brand_info["domain"]}
        ).eq("id", analysis_id).execute()
        _update_progress(db, analysis_id, progress, status="generating_prompts")

        # Step 2: Generate personalized prompts
        logger.info(f"[{analysis_id}] Generating search prompts")
        prompts = await prompt_generator.generate_prompts(
            brand_name=brand_info["name"],
            brand_description=brand_info.get("description", ""),
            competitors=discovered,
            cost_tracker=costs,
        )

        # Insert prompts
        db_prompts = []
        for p in prompts:
            result = (
                db.table("prompts")
                .insert(
                    {
                        "analysis_id": analysis_id,
                        "prompt_text": p["prompt_text"],
                        "category": p["category"],
                    }
                )
                .execute()
            )
            db_prompts.append(result.data[0])

        progress["prompts_generated"] = len(db_prompts)
        logger.info(f"[{analysis_id}] Generated {len(db_prompts)} prompts")

        # ── Status: querying_engines ─────────────────────────────────
        num_prompts = len(db_prompts)
        engines = _active_engines(settings)
        skipped_engines = sorted(set(ENGINE_MODULES) - set(engines))
        if skipped_engines:
            logger.info(
                f"[{analysis_id}] Skipping engines (no credentials): "
                f"{', '.join(skipped_engines)}"
            )
        engine_progress = {
            name: {"completed": 0, "total": num_prompts}
            for name in engines
        }
        progress["engines"] = engine_progress
        _update_progress(db, analysis_id, progress, status="querying_engines")

        # Step 3: Run AI engine queries concurrently
        logger.info(
            f"[{analysis_id}] Querying {len(engines)} AI engines across {num_prompts} prompts"
        )
        semaphore = asyncio.Semaphore(settings.max_concurrent_prompts)
        all_citations = []
        all_brand_mentions = []
        engine_lock = asyncio.Lock()
        total_engine_completions = 0

        # Engines that return SearchResult with response text (LLM-based)
        LLM_ENGINES = {"openai", "gemini", "perplexity"}

        async def query_engine_for_prompt(engine_name: str, module, prompt_row: dict):
            nonlocal total_engine_completions
            async with semaphore:
                try:
                    search_text = prompt_row["prompt_text"] + f" — {brand_info['name']}"
                    result = await module.search(
                        search_text, cost_tracker=costs
                    )

                    # Handle both SearchResult and plain list[dict] (exa)
                    if isinstance(result, SearchResult):
                        citations = result.citations
                        response_text = result.response_text
                    else:
                        citations = result
                        response_text = ""

                    for cite in citations:
                        competitor_id = _match_citation_to_competitor(
                            cite["url"], all_competitors
                        )
                        citation_record = {
                            "analysis_id": analysis_id,
                            "prompt_id": prompt_row["id"],
                            "engine": engine_name,
                            "cited_url": cite["url"],
                            "cited_domain": _extract_domain(cite["url"]),
                            "cited_title": cite.get("title", ""),
                            "position": cite.get("position"),
                            "snippet": cite.get("snippet", ""),
                            "competitor_id": competitor_id,
                        }
                        all_citations.append(citation_record)

                    # Extract brand mentions from LLM response text
                    if engine_name in LLM_ENGINES and response_text:
                        mentions = await extract_brand_mentions(
                            response_text,
                            all_competitors,
                            cost_tracker=costs,
                            citations=citations,
                        )
                        for m in mentions:
                            all_brand_mentions.append(
                                {
                                    "analysis_id": analysis_id,
                                    "prompt_id": prompt_row["id"],
                                    "engine": engine_name,
                                    "brand_name": m["brand_name"],
                                    "normalized_name": m["normalized_name"],
                                    "position": m.get("position"),
                                    "context": m.get("context", ""),
                                    "competitor_id": m.get("competitor_id"),
                                    "source_citations": m.get("source_citations", []),
                                }
                            )

                except Exception as e:
                    logger.error(
                        f"[{analysis_id}] Engine {engine_name} failed for prompt {prompt_row['id']}: {e}"
                    )

                # Update engine progress (always, even on failure)
                async with engine_lock:
                    engine_progress[engine_name]["completed"] += 1
                    total_engine_completions += 1
                    # Throttle DB writes: every N completions or on last completion
                    total_tasks = num_prompts * len(engines)
                    if (
                        total_engine_completions % _ENGINE_PROGRESS_WRITE_INTERVAL == 0
                        or total_engine_completions == total_tasks
                    ):
                        progress["engines"] = engine_progress
                        _update_progress(db, analysis_id, progress)

        tasks = []
        for prompt_row in db_prompts:
            for engine_name, module in engines.items():
                tasks.append(
                    query_engine_for_prompt(engine_name, module, prompt_row)
                )

        await asyncio.gather(*tasks)

        # ── Status: scoring ──────────────────────────────────────────
        _update_progress(db, analysis_id, progress, status="scoring")

        # Step 4: Batch insert citations
        logger.info(f"[{analysis_id}] Inserting {len(all_citations)} citations")
        if all_citations:
            for i in range(0, len(all_citations), 100):
                batch = all_citations[i : i + 100]
                db.table("citations").insert(batch).execute()

        progress["citations_found"] = len(all_citations)

        # Step 4b: Batch insert brand mentions
        logger.info(f"[{analysis_id}] Inserting {len(all_brand_mentions)} brand mentions")
        if all_brand_mentions:
            for i in range(0, len(all_brand_mentions), 100):
                batch = all_brand_mentions[i : i + 100]
                db.table("brand_mentions").insert(batch).execute()

        progress["brands_found"] = len(all_brand_mentions)
        _update_progress(db, analysis_id, progress)

        # Reload citations with IDs for scoring
        db_citations = (
            db.table("citations")
            .select("*")
            .eq("analysis_id", analysis_id)
            .execute()
        )

        # Reload brand mentions for scoring
        db_brand_mentions = (
            db.table("brand_mentions")
            .select("*")
            .eq("analysis_id", analysis_id)
            .execute()
        )

        # Step 5: Calculate and store scores
        logger.info(f"[{analysis_id}] Calculating visibility scores")
        scores = scoring.calculate_scores(
            competitors=all_competitors,
            citations=db_citations.data,
            prompts=db_prompts,
            brand_mentions=db_brand_mentions.data,
        )

        if scores:
            for i in range(0, len(scores), 100):
                batch = scores[i : i + 100]
                score_records = [
                    {
                        "analysis_id": analysis_id,
                        "competitor_id": s["competitor_id"],
                        "engine": s["engine"],
                        "visibility_score": s["visibility_score"],
                        "share_of_voice": s["share_of_voice"],
                        "citation_count": s["citation_count"],
                        "avg_position": s["avg_position"],
                    }
                    for s in batch
                ]
                db.table("visibility_scores").insert(score_records).execute()

        # Step 6: Mark as completed
        db.table("analyses").update(
            {"status": "completed", "completed_at": "now()"}
        ).eq("id", analysis_id).execute()

        # Log cost summary
        costs.log_summary(analysis_id)
        logger.info(f"[{analysis_id}] Analysis completed successfully")

    except Exception as e:
        logger.error(f"[{analysis_id}] Analysis failed: {e}")
        costs.log_summary(analysis_id)
        db.table("analyses").update({"status": "failed"}).eq(
            "id", analysis_id
        ).execute()
        raise
