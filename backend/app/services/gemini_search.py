import logging

from openai import AsyncOpenAI

from app.config import get_settings
from app.services.citation_parser import SearchResult, extract_citations_from_response
from app.services.cost_tracker import CostTracker, extract_cost_from_response

logger = logging.getLogger(__name__)

OPENROUTER_MODEL = "google/gemini-2.0-flash-001"
NATIVE_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = (
    "Provide detailed information with specific tool, platform, and company "
    "recommendations. Cite your sources."
)


async def search(prompt: str, cost_tracker: CostTracker | None = None) -> SearchResult:
    """Query Gemini with web search.

    Routing:
    - If OPENROUTER_API_KEY is set, route through OpenRouter (legacy path).
    - Else if GEMINI_API_KEY is set, hit Google AI Studio directly with the
      google_search grounding tool.
    - Else log a warning and return an empty result.
    """
    settings = get_settings()

    if settings.openrouter_api_key:
        return await _search_via_openrouter(prompt, cost_tracker, settings)
    if settings.gemini_api_key:
        return await _search_via_gemini_native(prompt, cost_tracker, settings)

    logger.warning(
        "Gemini search skipped: no API key configured "
        "(set OPENROUTER_API_KEY or GEMINI_API_KEY)"
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
            cost_tracker.record("gemini", OPENROUTER_MODEL, pt, ct, cost)

        citations = extract_citations_from_response(response)
        response_text = response.choices[0].message.content or ""
        return SearchResult(citations=citations, response_text=response_text)

    except Exception as e:
        logger.error(f"Gemini search (OpenRouter) failed for prompt '{prompt[:50]}': {e}")
        return SearchResult()


async def _search_via_gemini_native(
    prompt: str, cost_tracker: CostTracker | None, settings
) -> SearchResult:
    """Use Google AI Studio directly with the google_search grounding tool.

    Free-tier eligible. Returns grounding chunks which we translate into the
    citation dict shape the rest of the pipeline expects.
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.error(
            "Gemini native path requires `google-genai` — install with "
            "`pip install google-genai`"
        )
        return SearchResult()

    client = genai.Client(api_key=settings.gemini_api_key)

    try:
        response = await client.aio.models.generate_content(
            model=NATIVE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )

        response_text = response.text or ""
        citations = _extract_gemini_citations(response, response_text)

        if cost_tracker:
            usage = getattr(response, "usage_metadata", None)
            pt = getattr(usage, "prompt_token_count", 0) or 0
            ct = getattr(usage, "candidates_token_count", 0) or 0
            cost_tracker.record("gemini", NATIVE_MODEL, pt, ct, 0.0)

        return SearchResult(citations=citations, response_text=response_text)

    except Exception as e:
        logger.error(f"Gemini search (native) failed for prompt '{prompt[:50]}': {e}")
        return SearchResult()


def _extract_gemini_citations(response, response_text: str) -> list[dict]:
    """Pull URL citations out of Gemini's grounding_metadata.grounding_chunks.

    Gemini returns `web.uri` as a `vertexaisearch.cloud.google.com/grounding-api-redirect/...`
    redirect link, never the publisher's URL. The actual source domain is in
    `web.title` (e.g. "anaconda.com"). We synthesise an https:// URL from the
    title when it looks like a domain so the downstream domain extractor can
    match competitors; otherwise we fall back to the redirect URI.
    """
    citations: list[dict] = []
    seen_keys: set[str] = set()

    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return citations

    metadata = getattr(candidates[0], "grounding_metadata", None)
    if not metadata:
        return citations

    chunks = getattr(metadata, "grounding_chunks", None) or []
    position = 1
    for chunk in chunks:
        web = getattr(chunk, "web", None)
        if not web:
            continue
        redirect_uri = getattr(web, "uri", None)
        title = (getattr(web, "title", "") or "").strip()

        # Treat title as a domain when it has a dot, no spaces, and no path/scheme.
        title_looks_like_domain = (
            title
            and " " not in title
            and "." in title
            and "/" not in title
            and not title.startswith("http")
        )
        if title_looks_like_domain:
            cited_url = f"https://{title}"
            display_title = title
        elif redirect_uri:
            cited_url = redirect_uri
            display_title = title
        else:
            continue

        # Dedup by whichever key we ended up using
        key = cited_url
        if key in seen_keys:
            continue
        seen_keys.add(key)

        citations.append(
            {
                "url": cited_url,
                "title": display_title,
                "snippet": response_text[:200] if position == 1 else "",
                "position": position,
            }
        )
        position += 1

    return citations
