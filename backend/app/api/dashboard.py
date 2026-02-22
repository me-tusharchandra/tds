import logging

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    CitationListResponse,
    CitationResult,
    CompetitorListResponse,
    CompetitorResult,
    EngineBreakdownResponse,
    EngineScore,
    HistoryEntry,
    HistoryResponse,
    OverviewResponse,
    PromptResultEntry,
    PromptResultsResponse,
)
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_analysis_or_404(db, analysis_id: str) -> dict:
    result = db.table("analyses").select("*").eq("id", analysis_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return result.data[0]


@router.get("/analyses/{analysis_id}/overview", response_model=OverviewResponse)
async def get_overview(analysis_id: str):
    """Get analysis overview with visibility scores and share of voice."""
    db = get_supabase()
    analysis = _get_analysis_or_404(db, analysis_id)

    # Get primary brand's competitor record
    brand_comp = (
        db.table("competitors")
        .select("id")
        .eq("analysis_id", analysis_id)
        .eq("is_primary", True)
        .execute()
    )
    brand_comp_id = brand_comp.data[0]["id"] if brand_comp.data else None

    # Get brand's visibility scores
    scores_result = (
        db.table("visibility_scores")
        .select("*")
        .eq("analysis_id", analysis_id)
        .eq("competitor_id", brand_comp_id)
        .execute()
    ) if brand_comp_id else type("R", (), {"data": []})()

    overall_score = 0.0
    overall_sov = 0.0
    total_citations = 0
    engine_scores = []

    for s in scores_result.data:
        if s["engine"] == "overall":
            overall_score = s["visibility_score"] or 0
            overall_sov = s["share_of_voice"] or 0
            total_citations = s["citation_count"] or 0
        else:
            engine_scores.append(
                EngineScore(
                    engine=s["engine"],
                    visibility_score=s["visibility_score"] or 0,
                    share_of_voice=s["share_of_voice"] or 0,
                    citation_count=s["citation_count"] or 0,
                    avg_position=s.get("avg_position"),
                )
            )

    # Counts
    comp_count = (
        db.table("competitors")
        .select("id", count="exact")
        .eq("analysis_id", analysis_id)
        .eq("is_primary", False)
        .execute()
    )
    prompt_count = (
        db.table("prompts")
        .select("id", count="exact")
        .eq("analysis_id", analysis_id)
        .execute()
    )

    return OverviewResponse(
        analysis_id=analysis_id,
        brand_name=analysis.get("brand_name"),
        brand_url=analysis["brand_url"],
        status=analysis["status"],
        overall_visibility=overall_score,
        overall_sov=overall_sov,
        total_citations=total_citations,
        engines=engine_scores,
        competitor_count=comp_count.count or 0,
        prompt_count=prompt_count.count or 0,
    )


@router.get(
    "/analyses/{analysis_id}/competitors", response_model=CompetitorListResponse
)
async def get_competitors(analysis_id: str):
    """Get all competitors with their scores."""
    db = get_supabase()
    _get_analysis_or_404(db, analysis_id)

    comps = (
        db.table("competitors")
        .select("*")
        .eq("analysis_id", analysis_id)
        .order("is_primary", desc=True)
        .execute()
    )

    # Get scores for all competitors
    scores = (
        db.table("visibility_scores")
        .select("*")
        .eq("analysis_id", analysis_id)
        .execute()
    )

    # Build score map: comp_id -> {engine -> score_data}
    score_map: dict[str, dict] = {}
    for s in scores.data:
        comp_id = s["competitor_id"]
        if comp_id not in score_map:
            score_map[comp_id] = {}
        score_map[comp_id][s["engine"]] = s

    results = []
    for c in comps.data:
        comp_scores = score_map.get(c["id"], {})
        overall = comp_scores.get("overall", {})
        engine_breakdown = {
            e: {
                "visibility_score": comp_scores.get(e, {}).get("visibility_score", 0),
                "citation_count": comp_scores.get(e, {}).get("citation_count", 0),
            }
            for e in ["openai", "gemini", "perplexity", "exa"]
            if e in comp_scores
        }

        results.append(
            CompetitorResult(
                id=c["id"],
                name=c["name"],
                url=c["url"],
                domain=c.get("domain"),
                description=c.get("description"),
                is_primary=c["is_primary"],
                visibility_score=overall.get("visibility_score", 0),
                share_of_voice=overall.get("share_of_voice", 0),
                citation_count=overall.get("citation_count", 0),
                avg_position=overall.get("avg_position"),
                engines=engine_breakdown,
            )
        )

    # Sort: primary first, then by visibility score descending
    results.sort(key=lambda x: (-x.is_primary, -(x.visibility_score or 0)))
    return CompetitorListResponse(competitors=results)


@router.get(
    "/analyses/{analysis_id}/citations", response_model=CitationListResponse
)
async def get_citations(analysis_id: str, engine: str | None = None):
    """Get all citations, optionally filtered by engine."""
    db = get_supabase()
    _get_analysis_or_404(db, analysis_id)

    query = (
        db.table("citations")
        .select("*, competitors(name), prompts(prompt_text)")
        .eq("analysis_id", analysis_id)
        .order("engine")
        .order("position")
    )
    if engine:
        query = query.eq("engine", engine)

    result = query.execute()

    citations = [
        CitationResult(
            id=c["id"],
            engine=c["engine"],
            cited_url=c["cited_url"],
            cited_domain=c.get("cited_domain"),
            cited_title=c.get("cited_title"),
            position=c.get("position"),
            snippet=c.get("snippet"),
            competitor_name=(
                c["competitors"]["name"] if c.get("competitors") else None
            ),
            prompt_text=(
                c["prompts"]["prompt_text"] if c.get("prompts") else None
            ),
        )
        for c in result.data
    ]

    return CitationListResponse(citations=citations, total=len(citations))


@router.get(
    "/analyses/{analysis_id}/engines", response_model=EngineBreakdownResponse
)
async def get_engine_breakdown(analysis_id: str):
    """Get per-engine breakdown of scores."""
    db = get_supabase()
    analysis = _get_analysis_or_404(db, analysis_id)

    # Get primary brand
    brand_comp = (
        db.table("competitors")
        .select("id")
        .eq("analysis_id", analysis_id)
        .eq("is_primary", True)
        .execute()
    )
    brand_comp_id = brand_comp.data[0]["id"] if brand_comp.data else None

    # Get all citation counts per engine
    all_citations = (
        db.table("citations")
        .select("engine, id")
        .eq("analysis_id", analysis_id)
        .execute()
    )

    # Count per engine
    engine_counts: dict[str, int] = {}
    for c in all_citations.data:
        engine_counts[c["engine"]] = engine_counts.get(c["engine"], 0) + 1

    # Get brand scores per engine
    brand_scores_data = {}
    if brand_comp_id:
        scores = (
            db.table("visibility_scores")
            .select("*")
            .eq("analysis_id", analysis_id)
            .eq("competitor_id", brand_comp_id)
            .execute()
        )
        for s in scores.data:
            if s["engine"] != "overall":
                brand_scores_data[s["engine"]] = s["visibility_score"] or 0

    engines = []
    for engine_name in ["openai", "gemini", "perplexity", "exa"]:
        brand_score = brand_scores_data.get(engine_name, 0)
        engines.append(
            EngineScore(
                engine=engine_name,
                visibility_score=brand_score,
                share_of_voice=0,  # Calculated at brand level
                citation_count=engine_counts.get(engine_name, 0),
            )
        )

    return EngineBreakdownResponse(engines=engines, brand_scores=brand_scores_data)


@router.get(
    "/analyses/{analysis_id}/history", response_model=HistoryResponse
)
async def get_history(analysis_id: str):
    """Get historical visibility scores for the same brand URL."""
    db = get_supabase()
    analysis = _get_analysis_or_404(db, analysis_id)

    # Find all completed analyses for this brand
    all_analyses = (
        db.table("analyses")
        .select("*")
        .eq("brand_url", analysis["brand_url"])
        .eq("status", "completed")
        .order("created_at")
        .execute()
    )

    entries = []
    for a in all_analyses.data:
        # Get primary competitor for each analysis
        brand_comp = (
            db.table("competitors")
            .select("id")
            .eq("analysis_id", a["id"])
            .eq("is_primary", True)
            .execute()
        )
        if not brand_comp.data:
            continue

        overall = (
            db.table("visibility_scores")
            .select("*")
            .eq("analysis_id", a["id"])
            .eq("competitor_id", brand_comp.data[0]["id"])
            .eq("engine", "overall")
            .execute()
        )

        if overall.data:
            s = overall.data[0]
            entries.append(
                HistoryEntry(
                    analysis_id=a["id"],
                    created_at=a["created_at"],
                    visibility_score=s["visibility_score"] or 0,
                    share_of_voice=s["share_of_voice"] or 0,
                    citation_count=s["citation_count"] or 0,
                )
            )

    return HistoryResponse(
        brand_url=analysis["brand_url"],
        entries=entries,
    )


@router.get(
    "/analyses/{analysis_id}/prompts", response_model=PromptResultsResponse
)
async def get_prompt_results(analysis_id: str):
    """Get results grouped by prompt."""
    db = get_supabase()
    _get_analysis_or_404(db, analysis_id)

    prompts = (
        db.table("prompts")
        .select("*")
        .eq("analysis_id", analysis_id)
        .execute()
    )

    result_prompts = []
    for p in prompts.data:
        citations_data = (
            db.table("citations")
            .select("*, competitors(name)")
            .eq("prompt_id", p["id"])
            .order("engine")
            .order("position")
            .execute()
        )

        citations = [
            CitationResult(
                id=c["id"],
                engine=c["engine"],
                cited_url=c["cited_url"],
                cited_domain=c.get("cited_domain"),
                cited_title=c.get("cited_title"),
                position=c.get("position"),
                snippet=c.get("snippet"),
                competitor_name=(
                    c["competitors"]["name"] if c.get("competitors") else None
                ),
                prompt_text=p["prompt_text"],
            )
            for c in citations_data.data
        ]

        result_prompts.append(
            PromptResultEntry(
                prompt_id=p["id"],
                prompt_text=p["prompt_text"],
                category=p.get("category"),
                citations=citations,
            )
        )

    return PromptResultsResponse(prompts=result_prompts)
