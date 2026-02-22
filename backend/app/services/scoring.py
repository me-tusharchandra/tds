import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

ENGINES = ["openai", "gemini", "perplexity", "exa"]

# Engines that produce brand mentions (LLM-based, not exa)
MENTION_ENGINES = ["openai", "gemini", "perplexity"]


def calculate_scores(
    competitors: list[dict],
    citations: list[dict],
    prompts: list[dict],
    brand_mentions: list[dict] | None = None,
) -> list[dict]:
    """Calculate visibility scores and share of voice for each competitor per engine.

    Args:
        competitors: list of competitor dicts with 'id', 'domain', 'is_primary'
        citations: list of citation dicts with 'competitor_id', 'engine', 'prompt_id', 'position'
        prompts: list of prompt dicts with 'id'
        brand_mentions: optional list of brand mention dicts with 'competitor_id', 'engine', 'prompt_id', 'position'

    Returns:
        list of score dicts with keys: competitor_id, engine, visibility_score, share_of_voice, citation_count, avg_position
    """
    total_prompts = len(prompts)
    if total_prompts == 0:
        return []

    brand_mentions = brand_mentions or []
    has_mentions = len(brand_mentions) > 0

    # Group citations by (competitor_id, engine)
    comp_engine_citations: dict[tuple[str, str], list[dict]] = defaultdict(list)
    engine_total_citations: dict[str, int] = defaultdict(int)

    for c in citations:
        if c.get("competitor_id"):
            key = (c["competitor_id"], c["engine"])
            comp_engine_citations[key].append(c)
        engine_total_citations[c["engine"]] += 1

    # Group brand mentions by (competitor_id, engine)
    comp_engine_mentions: dict[tuple[str, str], list[dict]] = defaultdict(list)
    engine_total_mentions: dict[str, int] = defaultdict(int)

    for m in brand_mentions:
        if m.get("competitor_id"):
            key = (m["competitor_id"], m["engine"])
            comp_engine_mentions[key].append(m)
        engine_total_mentions[m["engine"]] += 1

    total_citations_all = len(citations)
    total_mentions_all = len(brand_mentions)

    scores = []

    for comp in competitors:
        comp_id = comp["id"]
        engine_scores_for_overall = []

        for engine in ENGINES:
            key = (comp_id, engine)
            engine_cites = comp_engine_citations.get(key, [])
            cite_count = len(engine_cites)

            # Citation-based presence rate
            prompts_cited = len({c["prompt_id"] for c in engine_cites if c.get("prompt_id")})
            citation_presence = prompts_cited / total_prompts if total_prompts > 0 else 0

            # Citation-based average position score
            if engine_cites:
                position_scores = [
                    1.0 / c["position"]
                    for c in engine_cites
                    if c.get("position") and c["position"] > 0
                ]
                cite_pos_score = (
                    sum(position_scores) / len(position_scores) if position_scores else 0
                )
                avg_position = (
                    sum(c["position"] for c in engine_cites if c.get("position"))
                    / len([c for c in engine_cites if c.get("position")])
                    if any(c.get("position") for c in engine_cites)
                    else None
                )
            else:
                cite_pos_score = 0
                avg_position = None

            # Citation-based visibility
            cite_visibility = (citation_presence * 0.6 + cite_pos_score * 0.4) * 100

            # Blend with mention-based visibility for LLM engines
            if has_mentions and engine in MENTION_ENGINES:
                engine_mentions = comp_engine_mentions.get(key, [])
                mention_count = len(engine_mentions)

                # Mention presence rate
                prompts_mentioned = len({m["prompt_id"] for m in engine_mentions if m.get("prompt_id")})
                mention_presence = prompts_mentioned / total_prompts if total_prompts > 0 else 0

                # Mention position score (1/position, same as citations)
                if engine_mentions:
                    mention_pos_scores = [
                        1.0 / m["position"]
                        for m in engine_mentions
                        if m.get("position") and m["position"] > 0
                    ]
                    mention_pos_score = (
                        sum(mention_pos_scores) / len(mention_pos_scores)
                        if mention_pos_scores
                        else 0
                    )
                else:
                    mention_pos_score = 0

                mention_visibility = (mention_presence * 0.6 + mention_pos_score * 0.4) * 100

                # Blend 50/50 citation + mention visibility
                visibility = (cite_visibility + mention_visibility) / 2
            else:
                visibility = cite_visibility

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

            if cite_count > 0 or (has_mentions and comp_engine_mentions.get(key)):
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
