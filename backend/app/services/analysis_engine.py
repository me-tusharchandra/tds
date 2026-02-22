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
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

ENGINE_MODULES = {
    "openai": openai_search,
    "gemini": gemini_search,
    "perplexity": perplexity_search,
    "exa": exa_search,
}


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


async def run_analysis(analysis_id: str, brand_url: str) -> None:
    """Run the full analysis pipeline for a brand URL."""
    db = get_supabase()
    settings = get_settings()

    try:
        # Update status to discovering
        db.table("analyses").update({"status": "discovering"}).eq(
            "id", analysis_id
        ).execute()

        # Step 1: Discover competitors
        logger.info(f"[{analysis_id}] Discovering competitors for {brand_url}")
        discovery = await competitor_discovery.discover_competitors(brand_url)
        brand_info = discovery["brand_info"]

        # Update analysis with brand info
        db.table("analyses").update(
            {
                "brand_name": brand_info["name"],
                "brand_domain": brand_info["domain"],
                "status": "analyzing",
            }
        ).eq("id", analysis_id).execute()

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

        # Insert discovered competitors
        for comp in discovery["competitors"]:
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

        # Step 2: Generate prompts
        logger.info(f"[{analysis_id}] Generating search prompts")
        prompts = await prompt_generator.generate_prompts(
            brand_name=brand_info["name"],
            brand_description=brand_info.get("description", ""),
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

        # Step 3: Run AI engine queries concurrently
        logger.info(f"[{analysis_id}] Querying {len(ENGINE_MODULES)} AI engines across {len(db_prompts)} prompts")
        semaphore = asyncio.Semaphore(settings.max_concurrent_prompts)
        all_citations = []

        async def query_engine_for_prompt(engine_name: str, module, prompt_row: dict):
            async with semaphore:
                try:
                    results = await module.search(prompt_row["prompt_text"])
                    for cite in results:
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
                except Exception as e:
                    logger.error(
                        f"[{analysis_id}] Engine {engine_name} failed for prompt {prompt_row['id']}: {e}"
                    )

        # Create all tasks
        tasks = []
        for prompt_row in db_prompts:
            for engine_name, module in ENGINE_MODULES.items():
                tasks.append(
                    query_engine_for_prompt(engine_name, module, prompt_row)
                )

        await asyncio.gather(*tasks)

        # Step 4: Batch insert citations
        logger.info(f"[{analysis_id}] Inserting {len(all_citations)} citations")
        if all_citations:
            # Insert in batches of 100
            for i in range(0, len(all_citations), 100):
                batch = all_citations[i : i + 100]
                db.table("citations").insert(batch).execute()

        # Reload citations with IDs for scoring
        db_citations = (
            db.table("citations")
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
        logger.info(f"[{analysis_id}] Analysis completed successfully")

    except Exception as e:
        logger.error(f"[{analysis_id}] Analysis failed: {e}")
        db.table("analyses").update({"status": "failed"}).eq(
            "id", analysis_id
        ).execute()
        raise
