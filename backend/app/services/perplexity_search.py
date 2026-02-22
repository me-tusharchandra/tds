import logging

from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


async def search(prompt: str) -> list[dict]:
    """Query Perplexity Sonar with web search and extract citations.

    Returns list of dicts with keys: url, title, snippet, position
    """
    settings = get_settings()
    client = AsyncOpenAI(
        api_key=settings.perplexity_api_key,
        base_url="https://api.perplexity.ai",
    )

    try:
        response = await client.chat.completions.create(
            model="sonar",
            messages=[
                {
                    "role": "system",
                    "content": "Provide accurate, detailed information with citations. List specific tools, platforms, and companies by name.",
                },
                {"role": "user", "content": prompt},
            ],
        )

        # Citations are in model_extra (Perplexity extension)
        raw = response.model_extra or {}
        citation_urls = raw.get("citations", [])
        content = response.choices[0].message.content or ""

        citations = []
        seen_urls: set[str] = set()

        for i, url in enumerate(citation_urls):
            if url not in seen_urls:
                seen_urls.add(url)
                citations.append(
                    {
                        "url": url,
                        "title": "",
                        "snippet": content[:200] if i == 0 else "",
                        "position": i + 1,
                    }
                )

        return citations

    except Exception as e:
        logger.error(f"Perplexity search failed for prompt '{prompt[:50]}': {e}")
        return []
