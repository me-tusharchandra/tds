import logging
from urllib.parse import urlparse

from exa_py import Exa

from app.config import get_settings

logger = logging.getLogger(__name__)


def _extract_domain(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    domain = domain.lower().removeprefix("www.")
    return domain


def _extract_brand_name(url: str, title: str | None = None) -> str:
    if title:
        # Clean common suffixes
        for sep in [" - ", " | ", " — ", " · "]:
            if sep in title:
                return title.split(sep)[0].strip()
        return title.strip()
    domain = _extract_domain(url)
    name = domain.split(".")[0]
    return name.capitalize()


async def discover_competitors(
    brand_url: str,
    num_results: int = 10,
) -> dict:
    """Discover competitors for a brand using Exa AI.

    Returns dict with keys: brand_info, competitors
    """
    settings = get_settings()
    exa = Exa(api_key=settings.exa_api_key)
    brand_domain = _extract_domain(brand_url)

    # Step 1: Get brand info via contents
    try:
        brand_contents = exa.get_contents(
            urls=[brand_url],
            text={"max_characters": 2000},
            summary=True,
        )
        brand_result = brand_contents.results[0] if brand_contents.results else None
        brand_name = _extract_brand_name(
            brand_url, brand_result.title if brand_result else None
        )
        brand_description = (
            brand_result.summary if brand_result and brand_result.summary else ""
        )
    except Exception as e:
        logger.warning(f"Could not fetch brand info: {e}")
        brand_name = _extract_brand_name(brand_url)
        brand_description = ""

    # Step 2: Find similar companies
    seen_domains: set[str] = {brand_domain}
    competitors: list[dict] = []

    try:
        similar = exa.find_similar(
            url=brand_url,
            num_results=num_results,
            exclude_source_domain=True,
            category="company",
            contents={"text": {"max_characters": 500}, "summary": True},
        )
        for r in similar.results:
            domain = _extract_domain(r.url)
            if domain not in seen_domains:
                seen_domains.add(domain)
                competitors.append(
                    {
                        "name": _extract_brand_name(r.url, r.title),
                        "url": r.url,
                        "domain": domain,
                        "description": r.summary or (r.text[:200] if r.text else ""),
                    }
                )
    except Exception as e:
        logger.error(f"find_similar failed: {e}")

    # Step 3: Supplement with search if we have few results
    if len(competitors) < 5:
        try:
            search_results = exa.search(
                query=f"competitors of {brand_name}",
                num_results=10,
                category="company",
                contents={"text": {"max_characters": 500}, "summary": True},
            )
            for r in search_results.results:
                domain = _extract_domain(r.url)
                if domain not in seen_domains:
                    seen_domains.add(domain)
                    competitors.append(
                        {
                            "name": _extract_brand_name(r.url, r.title),
                            "url": r.url,
                            "domain": domain,
                            "description": r.summary
                            or (r.text[:200] if r.text else ""),
                        }
                    )
        except Exception as e:
            logger.error(f"Search for competitors failed: {e}")

    return {
        "brand_info": {
            "name": brand_name,
            "url": brand_url,
            "domain": brand_domain,
            "description": brand_description,
        },
        "competitors": competitors[:num_results],
    }
