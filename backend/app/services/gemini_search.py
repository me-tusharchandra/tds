import logging

import httpx
from google import genai
from google.genai import types

from app.config import get_settings

logger = logging.getLogger(__name__)


async def _resolve_redirect(url: str) -> str:
    """Resolve Vertex AI Search redirect URLs to actual URLs."""
    if "vertexaisearch" not in url:
        return url
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=5) as client:
            resp = await client.head(url)
            return str(resp.url)
    except Exception:
        return url


async def search(prompt: str) -> list[dict]:
    """Query Gemini with Google Search grounding and extract citations.

    Returns list of dicts with keys: url, title, snippet, position
    """
    settings = get_settings()
    client = genai.Client(api_key=settings.google_api_key)

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )

        citations = []
        seen_urls: set[str] = set()
        position = 1

        candidate = response.candidates[0] if response.candidates else None
        if not candidate or not candidate.grounding_metadata:
            return []

        metadata = candidate.grounding_metadata
        chunks = metadata.grounding_chunks or []

        # Build snippet map from grounding_supports
        snippet_map: dict[int, str] = {}
        if metadata.grounding_supports:
            for support in metadata.grounding_supports:
                if support.grounding_chunk_indices and support.segment:
                    for idx in support.grounding_chunk_indices:
                        if support.segment.text:
                            snippet_map[idx] = support.segment.text

        for i, chunk in enumerate(chunks):
            if not chunk.web:
                continue
            raw_url = chunk.web.uri
            resolved_url = await _resolve_redirect(raw_url)

            if resolved_url not in seen_urls:
                seen_urls.add(resolved_url)
                citations.append(
                    {
                        "url": resolved_url,
                        "title": chunk.web.title or "",
                        "snippet": snippet_map.get(i, ""),
                        "position": position,
                    }
                )
                position += 1

        return citations

    except Exception as e:
        logger.error(f"Gemini search failed for prompt '{prompt[:50]}': {e}")
        return []
