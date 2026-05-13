import logging

from openai import AsyncOpenAI

from app.config import get_settings
from app.services.citation_parser import SearchResult, extract_citations_from_response
from app.services.cost_tracker import CostTracker, extract_cost_from_response

logger = logging.getLogger(__name__)

MODEL = "perplexity/sonar"

SYSTEM_PROMPT = (
    "Provide accurate, detailed information with citations. "
    "List specific tools, platforms, and companies by name."
)


async def search(prompt: str, cost_tracker: CostTracker | None = None) -> SearchResult:
    """Query Perplexity Sonar via OpenRouter.

    Perplexity has no free tier, so there is no native fallback. When the
    OpenRouter key is unset this engine simply returns an empty result and
    the rest of the pipeline continues without it.
    """
    settings = get_settings()

    if not settings.openrouter_api_key:
        logger.info(
            "Perplexity search skipped: requires OPENROUTER_API_KEY "
            "(no native fallback — Perplexity API is paid-only)"
        )
        return SearchResult()

    client = AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        if cost_tracker:
            pt, ct, cost = extract_cost_from_response(response)
            cost_tracker.record("perplexity", MODEL, pt, ct, cost)

        citations = extract_citations_from_response(response)
        response_text = response.choices[0].message.content or ""
        return SearchResult(citations=citations, response_text=response_text)

    except Exception as e:
        logger.error(f"Perplexity search failed for prompt '{prompt[:50]}': {e}")
        return SearchResult()
