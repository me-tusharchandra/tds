import logging

from openai import AsyncOpenAI

from app.config import get_settings
from app.services.citation_parser import SearchResult, extract_citations_from_response
from app.services.cost_tracker import CostTracker, extract_cost_from_response

logger = logging.getLogger(__name__)

MODEL = "openai/gpt-4o"


async def search(prompt: str, cost_tracker: CostTracker | None = None) -> SearchResult:
    """Query GPT-4o with web search via OpenRouter and extract citations."""
    settings = get_settings()
    client = AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Provide detailed information with specific tool, platform, and company recommendations. Cite your sources.",
                },
                {"role": "user", "content": prompt},
            ],
            extra_body={
                "plugins": [{"id": "web", "max_results": 10}],
            },
        )

        if cost_tracker:
            pt, ct, cost = extract_cost_from_response(response)
            cost_tracker.record("openai", MODEL, pt, ct, cost)

        citations = extract_citations_from_response(response)
        response_text = response.choices[0].message.content or ""
        return SearchResult(citations=citations, response_text=response_text)

    except Exception as e:
        logger.error(f"OpenAI search failed for prompt '{prompt[:50]}': {e}")
        return SearchResult()
