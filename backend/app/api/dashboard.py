import logging

from fastapi import APIRouter, HTTPException

from collections import defaultdict

from app.models.schemas import (
    BrandMention,
    BrandMentionsResponse,
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
    TopCitedBrand,
    TopCitedBrandsResponse,
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

    # Get brand mention counts per competitor
    mention_counts: dict[str, int] = {}
    try:
        mentions = (
            db.table("brand_mentions")
            .select("competitor_id")
            .eq("analysis_id", analysis_id)
            .not_.is_("competitor_id", "null")
            .execute()
        )
        for m in mentions.data:
            cid = m["competitor_id"]
            mention_counts[cid] = mention_counts.get(cid, 0) + 1
    except Exception:
        pass  # Table may not exist for older analyses

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
                brand_mention_count=mention_counts.get(c["id"]),
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

    # Fetch brand mentions to map brands → citations via source_citations
    brand_lookup: dict[tuple[str, str], list[dict]] = defaultdict(list)
    try:
        mentions = (
            db.table("brand_mentions")
            .select("brand_name, prompt_id, engine, source_citations")
            .eq("analysis_id", analysis_id)
            .execute()
        )
        for m in (mentions.data or []):
            key = (m["prompt_id"], m["engine"])
            brand_lookup[key].append(m)
    except Exception:
        pass  # Graceful fallback for old analyses without source_citations

    def _get_mentioned_brands(prompt_id: str, cite_engine: str, cite_position: int | None) -> list[str]:
        """Find brands whose source_citations include this citation's position."""
        if cite_position is None:
            return []
        brands = []
        for m in brand_lookup.get((prompt_id, cite_engine), []):
            sc = m.get("source_citations") or []
            if cite_position in sc:
                brands.append(m["brand_name"])
        return brands

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
            mentioned_brands=_get_mentioned_brands(
                c.get("prompt_id", ""), c["engine"], c.get("position")
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

    # Fetch all brand mentions for this analysis to map to citations
    brand_lookup: dict[tuple[str, str], list[dict]] = defaultdict(list)
    try:
        all_mentions = (
            db.table("brand_mentions")
            .select("brand_name, prompt_id, engine, source_citations")
            .eq("analysis_id", analysis_id)
            .execute()
        )
        for m in (all_mentions.data or []):
            key = (m["prompt_id"], m["engine"])
            brand_lookup[key].append(m)
    except Exception:
        pass

    def _get_mentioned_brands(prompt_id: str, cite_engine: str, cite_position: int | None) -> list[str]:
        if cite_position is None:
            return []
        brands = []
        for m in brand_lookup.get((prompt_id, cite_engine), []):
            sc = m.get("source_citations") or []
            if cite_position in sc:
                brands.append(m["brand_name"])
        return brands

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
                mentioned_brands=_get_mentioned_brands(
                    p["id"], c["engine"], c.get("position")
                ),
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


@router.get(
    "/analyses/{analysis_id}/top-cited", response_model=TopCitedBrandsResponse
)
async def get_top_cited_brands(analysis_id: str):
    """Get top 5 most-cited domains from actual citation data.

    Always includes the user's own brand domain (marked is_primary),
    even if it's not in the top 5.
    """
    db = get_supabase()
    analysis = _get_analysis_or_404(db, analysis_id)

    # Get the primary brand's domain
    brand_comp = (
        db.table("competitors")
        .select("domain")
        .eq("analysis_id", analysis_id)
        .eq("is_primary", True)
        .execute()
    )
    brand_domain = brand_comp.data[0].get("domain") if brand_comp.data else None

    citations = (
        db.table("citations")
        .select("cited_domain, cited_url, cited_title, engine, position")
        .eq("analysis_id", analysis_id)
        .execute()
    )

    # Aggregate by domain
    domain_data: dict[str, dict] = defaultdict(
        lambda: {
            "count": 0,
            "positions": [],
            "engines": set(),
            "urls": [],
            "title": None,
        }
    )

    for c in citations.data:
        domain = c.get("cited_domain") or "unknown"
        d = domain_data[domain]
        d["count"] += 1
        if c.get("position"):
            d["positions"].append(c["position"])
        d["engines"].add(c["engine"])
        if c["cited_url"] not in d["urls"]:
            d["urls"].append(c["cited_url"])
        if not d["title"] and c.get("cited_title"):
            d["title"] = c["cited_title"]

    # Sort by citation count
    sorted_domains = sorted(
        domain_data.items(), key=lambda x: x[1]["count"], reverse=True
    )

    # Take top 5
    top_domains = sorted_domains[:5]
    top_domain_names = {d[0] for d in top_domains}

    # Ensure brand domain is included even if not in top 5
    brand_entry_from_overflow = None
    if brand_domain and brand_domain not in top_domain_names:
        # Find it in the full list
        for domain, data in sorted_domains:
            if domain == brand_domain:
                brand_entry_from_overflow = (domain, data)
                break

    def _make_brand(domain: str, data: dict, is_primary: bool) -> TopCitedBrand:
        avg_pos = (
            sum(data["positions"]) / len(data["positions"])
            if data["positions"]
            else None
        )
        return TopCitedBrand(
            domain=domain,
            citation_count=data["count"],
            avg_position=round(avg_pos, 1) if avg_pos else None,
            engines=sorted(data["engines"]),
            sample_urls=data["urls"][:3],
            sample_title=data["title"],
            is_primary=is_primary,
        )

    brands = []
    for domain, data in top_domains:
        is_primary = brand_domain is not None and domain == brand_domain
        brands.append(_make_brand(domain, data, is_primary))

    # If brand wasn't in top 5 but has citations, append it
    if brand_entry_from_overflow:
        brands.append(_make_brand(brand_entry_from_overflow[0], brand_entry_from_overflow[1], True))
    # If brand has zero citations, still show it
    elif brand_domain and brand_domain not in top_domain_names and brand_domain not in domain_data:
        brands.append(
            TopCitedBrand(
                domain=brand_domain,
                citation_count=0,
                avg_position=None,
                engines=[],
                sample_urls=[],
                sample_title=None,
                is_primary=True,
            )
        )

    return TopCitedBrandsResponse(brands=brands)


@router.get(
    "/analyses/{analysis_id}/brand-mentions",
    response_model=BrandMentionsResponse,
)
async def get_brand_mentions(analysis_id: str):
    """Get aggregated brand mentions extracted from AI engine responses."""
    db = get_supabase()
    analysis = _get_analysis_or_404(db, analysis_id)

    # Get primary brand info so we can always include it
    brand_comp = (
        db.table("competitors")
        .select("id, name, domain")
        .eq("analysis_id", analysis_id)
        .eq("is_primary", True)
        .execute()
    )
    brand_name = brand_comp.data[0]["name"] if brand_comp.data else None
    brand_comp_id = brand_comp.data[0]["id"] if brand_comp.data else None

    try:
        mentions = (
            db.table("brand_mentions")
            .select("*, competitors(name, is_primary)")
            .eq("analysis_id", analysis_id)
            .execute()
        )
    except Exception:
        # Table may not exist for older analyses
        return BrandMentionsResponse(brands=[], total=0)

    # Get total prompt count for presence rate calculation
    prompt_count = (
        db.table("prompts")
        .select("id", count="exact")
        .eq("analysis_id", analysis_id)
        .execute()
    )
    total_prompts = prompt_count.count or 1

    # Aggregate by normalized_name
    brand_data: dict[str, dict] = {}
    found_primary = False

    for m in (mentions.data or []):
        norm = m["normalized_name"]
        if norm not in brand_data:
            brand_data[norm] = {
                "brand_name": m["brand_name"],
                "normalized_name": norm,
                "count": 0,
                "positions": [],
                "engines": set(),
                "prompt_ids": set(),
                "competitor_name": None,
                "is_primary": False,
                "contexts": [],
            }

        d = brand_data[norm]
        d["count"] += 1
        if m.get("position"):
            d["positions"].append(m["position"])
        d["engines"].add(m["engine"])
        if m.get("prompt_id"):
            d["prompt_ids"].add(m["prompt_id"])
        if m.get("context") and len(d["contexts"]) < 3:
            d["contexts"].append(m["context"])

        comp = m.get("competitors")
        if comp:
            d["competitor_name"] = comp.get("name")
            if comp.get("is_primary", False):
                d["is_primary"] = True
                found_primary = True

    # Build response sorted by mention count
    brands = []
    for norm, d in sorted(brand_data.items(), key=lambda x: -x[1]["count"]):
        avg_pos = (
            sum(d["positions"]) / len(d["positions"]) if d["positions"] else None
        )
        prompt_count_for_brand = len(d["prompt_ids"])
        presence = prompt_count_for_brand / total_prompts if total_prompts > 0 else 0

        brands.append(
            BrandMention(
                brand_name=d["brand_name"],
                normalized_name=d["normalized_name"],
                mention_count=d["count"],
                avg_position=round(avg_pos, 1) if avg_pos else None,
                engines=sorted(d["engines"]),
                prompt_count=prompt_count_for_brand,
                presence_rate=round(presence * 100, 1),
                competitor_name=d["competitor_name"],
                is_primary=d["is_primary"],
                sample_contexts=d["contexts"],
            )
        )

    # Always include the primary brand, even with 0 mentions
    if not found_primary and brand_name:
        brands.append(
            BrandMention(
                brand_name=brand_name,
                normalized_name=brand_name.strip().lower(),
                mention_count=0,
                avg_position=None,
                engines=[],
                prompt_count=0,
                presence_rate=0,
                competitor_name=brand_name,
                is_primary=True,
                sample_contexts=[],
            )
        )

    return BrandMentionsResponse(brands=brands, total=len(brands))
