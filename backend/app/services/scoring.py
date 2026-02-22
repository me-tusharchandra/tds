import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

ENGINES = ["openai", "gemini", "perplexity", "exa"]


def calculate_scores(
    competitors: list[dict],
    citations: list[dict],
    prompts: list[dict],
) -> list[dict]:
    """Calculate visibility scores and share of voice for each competitor per engine.

    Args:
        competitors: list of competitor dicts with 'id', 'domain', 'is_primary'
        citations: list of citation dicts with 'competitor_id', 'engine', 'prompt_id', 'position'
        prompts: list of prompt dicts with 'id'

    Returns:
        list of score dicts with keys: competitor_id, engine, visibility_score, share_of_voice, citation_count, avg_position
    """
    total_prompts = len(prompts)
    if total_prompts == 0:
        return []

    prompt_ids = {p["id"] for p in prompts}

    # Group citations by (competitor_id, engine)
    comp_engine_citations: dict[tuple[str, str], list[dict]] = defaultdict(list)
    engine_total_citations: dict[str, int] = defaultdict(int)

    for c in citations:
        if c.get("competitor_id"):
            key = (c["competitor_id"], c["engine"])
            comp_engine_citations[key].append(c)
        engine_total_citations[c["engine"]] += 1

    # Also track overall totals
    total_citations_all = len(citations)

    scores = []

    for comp in competitors:
        comp_id = comp["id"]
        engine_scores_for_overall = []

        for engine in ENGINES:
            key = (comp_id, engine)
            engine_cites = comp_engine_citations.get(key, [])
            cite_count = len(engine_cites)

            # Presence rate: in how many unique prompts was this competitor cited?
            prompts_cited = len({c["prompt_id"] for c in engine_cites if c.get("prompt_id")})
            presence_rate = prompts_cited / total_prompts if total_prompts > 0 else 0

            # Average position score: mean of 1/position (higher = cited earlier)
            if engine_cites:
                position_scores = [
                    1.0 / c["position"]
                    for c in engine_cites
                    if c.get("position") and c["position"] > 0
                ]
                avg_pos_score = (
                    sum(position_scores) / len(position_scores) if position_scores else 0
                )
                avg_position = (
                    sum(c["position"] for c in engine_cites if c.get("position"))
                    / len([c for c in engine_cites if c.get("position")])
                    if any(c.get("position") for c in engine_cites)
                    else None
                )
            else:
                avg_pos_score = 0
                avg_position = None

            # Visibility score: weighted combination
            visibility = (presence_rate * 0.6 + avg_pos_score * 0.4) * 100

            # Share of voice for this engine
            engine_total = engine_total_citations.get(engine, 0)
            sov = (cite_count / engine_total * 100) if engine_total > 0 else 0

            scores.append(
                {
                    "competitor_id": comp_id,
                    "engine": engine,
                    "visibility_score": round(visibility, 2),
                    "share_of_voice": round(sov, 2),
                    "citation_count": cite_count,
                    "avg_position": round(avg_position, 2) if avg_position else None,
                }
            )

            if cite_count > 0:
                engine_scores_for_overall.append(visibility)

        # Overall score: average across engines
        overall_visibility = (
            sum(engine_scores_for_overall) / len(engine_scores_for_overall)
            if engine_scores_for_overall
            else 0
        )

        # Overall citation count and SOV
        total_comp_citations = sum(
            len(comp_engine_citations.get((comp_id, e), []))
            for e in ENGINES
        )
        overall_sov = (
            (total_comp_citations / total_citations_all * 100)
            if total_citations_all > 0
            else 0
        )

        scores.append(
            {
                "competitor_id": comp_id,
                "engine": "overall",
                "visibility_score": round(overall_visibility, 2),
                "share_of_voice": round(overall_sov, 2),
                "citation_count": total_comp_citations,
                "avg_position": None,
            }
        )

    return scores
