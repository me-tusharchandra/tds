import logging

from openai import AsyncOpenAI

from app.config import get_settings
from app.services.citation_parser import SearchResult, extract_citations_from_response
from app.services.cost_tracker import CostTracker, extract_cost_from_response

logger = logging.getLogger(__name__)

OPENROUTER_MODEL = "openai/gpt-4o"
NATIVE_MODEL = "gpt-4o-search-preview"

SYSTEM_PROMPT = (
    "Provide detailed information with specific tool, platform, and company "
    "recommendations. Cite your sources."
)


async def search(prompt: str, cost_tracker: CostTracker | None = None) -> SearchResult:
    """Query GPT-4o with web search.

    Routing:
    - If OPENROUTER_API_KEY is set, route through OpenRouter (legacy path).
    - Else if OPENAI_API_KEY is set, hit OpenAI directly via Chat Completions
      with the built-in web_search_options tool.
    - Else log a warning and return an empty result.
    """
    settings = get_settings()

    if settings.openrouter_api_key:
        return await _search_via_openrouter(prompt, cost_tracker, settings)
    if settings.openai_api_key:
        return await _search_via_openai_native(prompt, cost_tracker, settings)

    logger.warning(
        "OpenAI search skipped: no API key configured "
        "(set OPENROUTER_API_KEY or OPENAI_API_KEY)"
    )
    return SearchResult()


async def _search_via_openrouter(
    prompt: str, cost_tracker: CostTracker | None, settings
) -> SearchResult:
    client = AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )

    try:
        response = await client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            extra_body={
                "plugins": [{"id": "web", "max_results": 10}],
            },
        )

        if cost_tracker:
            pt, ct, cost = extract_cost_from_response(response)
            cost_tracker.record("openai", OPENROUTER_MODEL, pt, ct, cost)

        citations = extract_citations_from_response(response)
        response_text = response.choices[0].message.content or ""
        return SearchResult(citations=citations, response_text=response_text)

    except Exception as e:
        logger.error(f"OpenAI search (OpenRouter) failed for prompt '{prompt[:50]}': {e}")
        return SearchResult()


async def _search_via_openai_native(
    prompt: str, cost_tracker: CostTracker | None, settings
) -> SearchResult:
    """Use OpenAI directly with the gpt-4o-search-preview model.

    The search model exposes web search natively and returns url_citation
    annotations in the same shape as OpenRouter, so the shared parser works.
    """
    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    try:
        response = await client.chat.completions.create(
            model=NATIVE_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            web_search_options={"search_context_size": "medium"},
        )

        if cost_tracker:
            pt, ct, _ = extract_cost_from_response(response)
            cost_tracker.record("openai", NATIVE_MODEL, pt, ct, 0.0)

        citations = extract_citations_from_response(response)
        response_text = response.choices[0].message.content or ""
        return SearchResult(citations=citations, response_text=response_text)

    except Exception as e:
        logger.error(f"OpenAI search (native) failed for prompt '{prompt[:50]}': {e}")
        return SearchResult()
