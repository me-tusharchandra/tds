"""Extract brand/product mentions from AI engine response text."""

import json
import logging
import re

from app.services.competitor_discovery import EXCLUDED_DOMAINS
from app.services.cost_tracker import CostTracker, extract_cost_from_response
from app.services.llm_client import get_llm

logger = logging.getLogger(__name__)

# Suffixes to strip when normalizing brand names
_DOMAIN_SUFFIXES = re.compile(r"\.(com|io|ai|co|app|dev|org|net)$", re.IGNORECASE)


def _normalize_brand(name: str) -> str:
    """Normalize a brand name for deduplication: lowercase, strip domain suffixes."""
    n = name.strip().lower()
    n = _DOMAIN_SUFFIXES.sub("", n)
    return n


def _is_excluded_brand(name: str) -> bool:
    """Check if a brand name matches an excluded domain."""
    normalized = _normalize_brand(name)
    for domain in EXCLUDED_DOMAINS:
        # Strip TLD from the excluded domain for comparison
        domain_base = domain.split(".")[0]
        if normalized == domain_base or normalized == domain:
            return True
    return False


def _match_to_competitor(
    normalized_name: str, competitors: list[dict]
) -> str | None:
    """Match a normalized brand name to a known competitor, return competitor_id."""
    for comp in competitors:
        comp_name = _normalize_brand(comp.get("name", ""))
        comp_domain = comp.get("domain", "").lower().removeprefix("www.")
        comp_domain_base = comp_domain.split(".")[0] if comp_domain else ""

        if normalized_name == comp_name:
            return comp["id"]
        if comp_domain_base and normalized_name == comp_domain_base:
            return comp["id"]
    return None


async def extract_brand_mentions(
    response_text: str,
    known_competitors: list[dict],
    cost_tracker: CostTracker | None = None,
    citations: list[dict] | None = None,
) -> list[dict]:
    """Extract brand/product mentions from LLM response text.

    Args:
        response_text: The raw text from an AI engine response.
        known_competitors: List of competitor dicts with 'id', 'name', 'domain'.
        cost_tracker: Optional cost tracker.
        citations: Optional list of citation dicts with 'url', 'position', etc.

    Returns:
        List of dicts with keys: brand_name, normalized_name, position, context,
        competitor_id, source_citations
    """
    if not response_text or len(response_text.strip()) < 20:
        return []

    llm = get_llm(kind="mini")
    if llm is None:
        logger.warning(
            "[Brand Extractor] No LLM credentials available — skipping extraction"
        )
        return []

    # Build citation context for the prompt
    has_citations = bool(citations)
    citation_instruction = ""
    if has_citations:
        citation_instruction = (
            '- "source_citations": array of citation position numbers (integers) '
            "that discuss or are associated with this brand. "
            "Only include positions from the CITATIONS list below. "
            "If a brand is not clearly linked to any citation, use an empty array.\n"
        )

    # Build user message with optional citation context
    user_parts = []
    if has_citations:
        citation_lines = []
        for c in citations:
            pos = c.get("position", "?")
            url = c.get("url", "")
            citation_lines.append(f"[{pos}] {url}")
        user_parts.append("CITATIONS:\n" + "\n".join(citation_lines))
        user_parts.append("")  # blank line separator

    user_parts.append("RESPONSE TEXT:\n" + response_text[:3000])
    user_message = "\n".join(user_parts)

    try:
        response = await llm.client.chat.completions.create(
            model=llm.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract all brand, product, tool, or company names mentioned in the text. "
                        "Return a JSON array of objects with:\n"
                        '- "name": the brand/product name exactly as mentioned\n'
                        '- "position": order of first appearance (1-based)\n'
                        '- "context": the sentence or phrase where it appears\n'
                        + citation_instruction
                        + "\nOnly include actual products, tools, platforms, or companies. "
                        "Exclude generic terms, technologies (Python, JavaScript), "
                        "and broad categories. Return ONLY the JSON array."
                    ),
                },
                {"role": "user", "content": user_message},
            ],
            max_tokens=1000,
            temperature=0,
        )

        if cost_tracker:
            pt, ct, cost = extract_cost_from_response(response)
            cost_tracker.record("brand_extraction", llm.model, pt, ct, cost)

        raw = response.choices[0].message.content.strip()

        # Handle markdown code blocks
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0]
        raw = raw.strip()

        mentions_raw = json.loads(raw)
        if not isinstance(mentions_raw, list):
            logger.warning("[Brand Extractor] LLM returned non-list")
            return []

        # Process and filter mentions
        results = []
        seen_normalized: set[str] = set()

        for m in mentions_raw:
            name = m.get("name", "").strip()
            if not name:
                continue

            normalized = _normalize_brand(name)
            if not normalized or len(normalized) < 2:
                continue

            # Skip excluded brands (social media, review sites, etc.)
            if _is_excluded_brand(name):
                continue

            # Deduplicate within this response
            if normalized in seen_normalized:
                continue
            seen_normalized.add(normalized)

            # Match to known competitor
            competitor_id = _match_to_competitor(normalized, known_competitors)

            # Parse source_citations if available
            raw_sc = m.get("source_citations")
            source_citations = []
            if isinstance(raw_sc, list):
                source_citations = [
                    int(x) for x in raw_sc if isinstance(x, (int, float))
                ]

            results.append(
                {
                    "brand_name": name,
                    "normalized_name": normalized,
                    "position": m.get("position"),
                    "context": (m.get("context") or "")[:500],
                    "competitor_id": competitor_id,
                    "source_citations": source_citations,
                }
            )

        logger.info(
            f"[Brand Extractor] Extracted {len(results)} brands from "
            f"{len(response_text)} chars of text"
        )
        return results

    except json.JSONDecodeError as e:
        logger.warning(f"[Brand Extractor] Failed to parse JSON: {e}")
        return []
    except Exception as e:
        logger.error(f"[Brand Extractor] Extraction failed: {e}")
        return []
