import json
import logging
from urllib.parse import urlparse

from exa_py import Exa

from app.config import get_settings
from app.services.cost_tracker import CostTracker, extract_cost_from_response
from app.services.llm_client import get_llm, get_search_llm

logger = logging.getLogger(__name__)

# Domains that are never competitors
EXCLUDED_DOMAINS = {
    "linkedin.com", "facebook.com", "twitter.com", "x.com", "instagram.com",
    "tiktok.com", "pinterest.com", "reddit.com", "threads.net",
    "youtube.com", "youtu.be", "vimeo.com",
    "github.com", "gitlab.com", "bitbucket.org", "stackoverflow.com",
    "google.com", "bing.com", "yahoo.com", "duckduckgo.com",
    "crunchbase.com", "g2.com", "capterra.com", "trustpilot.com",
    "glassdoor.com", "producthunt.com", "ycombinator.com",
    "techcrunch.com", "bloomberg.com", "forbes.com",
    "medium.com", "substack.com", "wordpress.com", "blogspot.com",
    "wikipedia.org", "wikimedia.org", "archive.org",
    "apps.apple.com", "play.google.com",
    "aws.amazon.com", "cloud.google.com", "azure.microsoft.com", "amazon.com",
}


def _is_excluded_domain(domain: str) -> bool:
    for excluded in EXCLUDED_DOMAINS:
        if domain == excluded or domain.endswith("." + excluded):
            return True
    return False


def _extract_domain(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    domain = domain.lower().removeprefix("www.")
    return domain


def _extract_brand_name(url: str, title: str | None = None) -> str:
    if title:
        for sep in [" - ", " | ", " — ", " · "]:
            if sep in title:
                return title.split(sep)[0].strip()
        return title.strip()
    domain = _extract_domain(url)
    name = domain.split(".")[0]
    return name.capitalize()


async def _get_brand_info(
    brand_url: str, exa: Exa, cost_tracker: CostTracker | None
) -> tuple[str, str, str]:
    """Step 1: Use Exa to fetch brand page content and summary.
    Returns (brand_name, brand_text, brand_summary).
    """
    brand_name = _extract_brand_name(brand_url)
    brand_text = ""
    brand_summary = ""

    try:
        logger.info(f"[Discovery] Step 1: Fetching brand info via Exa get_contents")
        brand_contents = exa.get_contents(
            urls=[brand_url],
            text={"max_characters": 3000},
            summary=True,
        )
        if cost_tracker:
            cost_tracker.record_exa("get_contents")

        brand_result = brand_contents.results[0] if brand_contents.results else None
        if brand_result:
            brand_name = _extract_brand_name(brand_url, brand_result.title)
            brand_text = brand_result.text or ""
            brand_summary = brand_result.summary or ""
            logger.info(f"[Discovery]   title    = {brand_result.title}")
            logger.info(f"[Discovery]   summary  = {brand_summary[:200]}")
            logger.info(f"[Discovery]   text_len = {len(brand_text)} chars")
        else:
            logger.warning(f"[Discovery]   get_contents returned no results")
    except Exception as e:
        logger.warning(f"[Discovery]   get_contents failed: {e}")

    return brand_name, brand_text, brand_summary


async def _summarize_brand(
    brand_name: str, brand_text: str, cost_tracker: CostTracker | None
) -> str:
    """Step 2: Use LLM to create a feature-focused summary."""
    logger.info(f"[Discovery] Step 2: Summarizing brand via LLM")
    llm = get_llm(kind="mini")
    if llm is None:
        logger.warning(
            "[Discovery]   No LLM credentials — skipping LLM brand summary"
        )
        return ""

    try:
        response = await llm.client.chat.completions.create(
            model=llm.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Given a brand name and its website text, write a 1-2 sentence "
                        "description of what the product/service does, its key features, "
                        "and target audience. Focus on WHAT it does, not WHO it is."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Brand: {brand_name}\n\nWebsite text:\n{brand_text[:2000]}",
                },
            ],
            max_tokens=150,
            temperature=0,
        )
        if cost_tracker:
            pt, ct, cost = extract_cost_from_response(response)
            cost_tracker.record("brand_summary", llm.model, pt, ct, cost)
        summary = response.choices[0].message.content.strip()
        logger.info(f"[Discovery]   LLM summary: {summary}")
        return summary
    except Exception as e:
        logger.warning(f"[Discovery]   Brand summarization failed: {e}")
        return ""


async def _discover_via_search_llm(
    brand_name: str,
    brand_description: str,
    brand_domain: str,
    num_results: int,
    cost_tracker: CostTracker | None,
) -> list[dict]:
    """Step 3: Ask a web-search-capable LLM to identify actual competitors.

    Uses Perplexity via OpenRouter when available, otherwise falls back to
    OpenAI's gpt-4o-search-preview which has built-in web search.
    """
    llm = get_search_llm()
    if llm is None:
        logger.warning(
            "[Discovery] Step 3 skipped: no search-capable LLM credentials available"
        )
        return []

    logger.info(
        f"[Discovery] Step 3: Asking {llm.provider}/{llm.model} for competitors"
    )

    prompt = f"""I need to find the top {num_results} direct competitors to "{brand_name}" ({brand_domain}).

Here's what {brand_name} does: {brand_description}

List exactly {num_results} direct competitors — companies/products that serve the same target audience and solve the same problem. Only include actual product companies, NOT:
- Social media profiles (LinkedIn, YouTube, Twitter, etc.)
- Review/aggregator sites (G2, Capterra, etc.)
- News articles or blog posts
- Generic platforms (AWS, Google Cloud, etc.)

Return a JSON array with objects containing:
- "name": company/product name
- "url": their main website URL (homepage, not a social profile)
- "reason": one sentence on why they compete with {brand_name}

Return ONLY the JSON array, no other text."""

    # Per-provider tuning: OpenRouter's perplexity/sonar accepts temperature/max_tokens;
    # OpenAI's gpt-4o-search-preview needs web_search_options instead of plugins.
    create_kwargs: dict = {
        "model": llm.model,
        "messages": [
            {
                "role": "system",
                "content": "You are a competitive intelligence analyst. Return only valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    if llm.provider == "openrouter":
        create_kwargs["max_tokens"] = 1000
        create_kwargs["temperature"] = 0
    else:
        # gpt-4o-search-preview rejects temperature and exposes web_search_options
        create_kwargs["web_search_options"] = {"search_context_size": "medium"}

    try:
        response = await llm.client.chat.completions.create(**create_kwargs)
        if cost_tracker:
            pt, ct, cost = extract_cost_from_response(response)
            cost_tracker.record("competitor_discovery", llm.model, pt, ct, cost)

        raw = response.choices[0].message.content.strip()
        logger.info(f"[Discovery]   {llm.provider} raw response:\n{raw}")

        # Parse JSON — handle markdown code blocks
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0]
        raw = raw.strip()

        # Strip markdown code fences the search model sometimes wraps JSON in.
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0].strip()

        competitors = json.loads(raw)
        if not isinstance(competitors, list):
            logger.warning(
                f"[Discovery]   {llm.provider} returned non-list: {type(competitors)}"
            )
            return []

        logger.info(
            f"[Discovery]   {llm.provider} identified {len(competitors)} competitors:"
        )
        for i, c in enumerate(competitors):
            logger.info(f"    [{i+1}] {c.get('name')} | {c.get('url')} | {c.get('reason', '')[:80]}")

        return competitors

    except json.JSONDecodeError as e:
        logger.error(f"[Discovery]   Failed to parse {llm.provider} JSON: {e}")
        return []
    except Exception as e:
        logger.error(f"[Discovery]   {llm.provider} competitor discovery failed: {e}")
        return []


async def _enrich_with_exa(
    competitors_raw: list[dict],
    brand_domain: str,
    exa: Exa,
    cost_tracker: CostTracker | None,
) -> list[dict]:
    """Step 4: Enrich Perplexity results with Exa data (descriptions, verified URLs).
    Also filters out excluded domains and duplicates.
    """
    logger.info(f"[Discovery] Step 4: Enriching {len(competitors_raw)} competitors via Exa")

    seen_domains: set[str] = {brand_domain}
    enriched: list[dict] = []

    # Collect URLs to fetch from Exa
    urls_to_fetch = []
    for c in competitors_raw:
        url = c.get("url", "")
        if not url:
            continue
        domain = _extract_domain(url)
        if domain in seen_domains:
            logger.info(f"[Discovery]   SKIP (duplicate): {c.get('name')} | {domain}")
            continue
        if _is_excluded_domain(domain):
            logger.info(f"[Discovery]   SKIP (excluded): {c.get('name')} | {domain}")
            continue
        seen_domains.add(domain)
        urls_to_fetch.append((c, url, domain))

    if not urls_to_fetch:
        return enriched

    # Batch fetch content from Exa for verified descriptions
    try:
        all_urls = [u[1] for u in urls_to_fetch]
        logger.info(f"[Discovery]   Fetching {len(all_urls)} URLs via Exa get_contents")
        contents = exa.get_contents(
            urls=all_urls,
            text={"max_characters": 500},
            summary=True,
        )
        if cost_tracker:
            cost_tracker.record_exa("get_contents")

        # Build a lookup by URL
        exa_by_url = {}
        for r in contents.results:
            exa_by_url[r.url] = r
            # Also index by domain for fuzzy matching (redirects, etc.)
            exa_by_url[_extract_domain(r.url)] = r
    except Exception as e:
        logger.warning(f"[Discovery]   Exa enrichment failed: {e}")
        exa_by_url = {}

    for raw_comp, url, domain in urls_to_fetch:
        exa_result = exa_by_url.get(url) or exa_by_url.get(domain)
        if exa_result:
            name = _extract_brand_name(exa_result.url, exa_result.title)
            description = exa_result.summary or (exa_result.text[:200] if exa_result.text else "")
            final_url = exa_result.url
        else:
            name = raw_comp.get("name", _extract_brand_name(url))
            description = raw_comp.get("reason", "")
            final_url = url

        enriched.append({
            "name": name,
            "url": final_url,
            "domain": domain,
            "description": description,
        })
        logger.info(f"[Discovery]   ENRICHED: {name} | {domain} | {final_url}")

    return enriched


async def discover_competitors(
    brand_url: str,
    num_results: int = 10,
    cost_tracker: CostTracker | None = None,
) -> dict:
    """Discover competitors using a multi-step pipeline:
    1. Exa get_contents — fetch brand page info
    2. LLM — summarize what the brand does
    3. Perplexity — identify actual competitors (reasoning + web search)
    4. Exa get_contents — enrich competitor data (descriptions, verified URLs)
    """
    settings = get_settings()
    exa = Exa(api_key=settings.exa_api_key)
    brand_domain = _extract_domain(brand_url)

    logger.info(f"[Discovery] === Starting competitor discovery for {brand_url} ===")
    logger.info(f"[Discovery] Brand domain: {brand_domain}")

    # Step 1: Get brand info from Exa
    brand_name, brand_text, brand_summary = await _get_brand_info(
        brand_url, exa, cost_tracker
    )

    # Step 2: LLM summarizes brand features
    brand_description = await _summarize_brand(
        brand_name, brand_text or brand_summary, cost_tracker
    )
    if not brand_description:
        brand_description = brand_summary
    logger.info(f"[Discovery] Final brand description: {brand_description}")

    # Step 3: Search-LLM identifies competitors (Perplexity if available, else gpt-4o-search-preview)
    discovered_raw = await _discover_via_search_llm(
        brand_name, brand_description, brand_domain, num_results, cost_tracker,
    )

    # Step 4: Enrich with Exa (descriptions, verified URLs, filtering)
    competitors = await _enrich_with_exa(
        discovered_raw, brand_domain, exa, cost_tracker
    )

    # If Perplexity returned too few, supplement with Exa find_similar
    if len(competitors) < 5:
        logger.info(
            f"[Discovery] Only {len(competitors)} competitors after Perplexity. "
            f"Running Exa find_similar fallback."
        )
        seen_domains = {brand_domain} | {c["domain"] for c in competitors}
        try:
            similar = exa.find_similar(
                url=brand_url,
                num_results=10,
                exclude_source_domain=True,
                category="company",
                contents={"text": {"max_characters": 500}, "summary": True},
            )
            if cost_tracker:
                cost_tracker.record_exa("find_similar")
            logger.info(f"[Discovery]   find_similar returned {len(similar.results)} results:")
            for ri, r in enumerate(similar.results):
                domain = _extract_domain(r.url)
                is_dupe = domain in seen_domains
                is_excluded = _is_excluded_domain(domain)
                skip_reason = (
                    "SKIPPED (duplicate)" if is_dupe
                    else "SKIPPED (excluded)" if is_excluded
                    else "ADDED"
                )
                logger.info(f"    [{ri+1}] {r.title or '(no title)'} | {r.url} | {skip_reason}")
                if not is_dupe and not is_excluded:
                    seen_domains.add(domain)
                    competitors.append({
                        "name": _extract_brand_name(r.url, r.title),
                        "url": r.url,
                        "domain": domain,
                        "description": r.summary or (r.text[:200] if r.text else ""),
                    })
        except Exception as e:
            logger.error(f"[Discovery]   find_similar failed: {e}")

    final = competitors[:num_results]
    logger.info(f"[Discovery] === Final competitor list ({len(final)}) ===")
    for i, c in enumerate(final):
        logger.info(f"  [{i+1}] {c['name']} | {c['domain']} | {c['url']}")

    return {
        "brand_info": {
            "name": brand_name,
            "url": brand_url,
            "domain": brand_domain,
            "description": brand_description,
        },
        "competitors": final,
    }
