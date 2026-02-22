import logging

from exa_py import Exa

from app.config import get_settings
from app.services.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


async def search(prompt: str, cost_tracker: CostTracker | None = None) -> list[dict]:
    """Query Exa AI search and extract citations."""
    settings = get_settings()
    exa = Exa(api_key=settings.exa_api_key)

    try:
        results = exa.search(
            prompt,
            num_results=10,
            type="auto",
            contents={"text": {"max_characters": 500}},
        )

        if cost_tracker:
            cost_tracker.record_exa("search")

        citations = []
        seen_urls: set[str] = set()
        position = 1

        for r in results.results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                citations.append(
                    {
                        "url": r.url,
                        "title": r.title or "",
                        "snippet": (r.text[:200] if r.text else ""),
                        "position": position,
                    }
                )
                position += 1

        return citations

    except Exception as e:
        logger.error(f"Exa search failed for prompt '{prompt[:50]}': {e}")
        return []
