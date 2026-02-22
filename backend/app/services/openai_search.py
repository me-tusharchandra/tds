import logging

from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


async def search(prompt: str) -> list[dict]:
    """Query OpenAI with web search and extract citations.

    Returns list of dicts with keys: url, title, snippet, position
    """
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    try:
        response = await client.responses.create(
            model="gpt-4o",
            tools=[
                {
                    "type": "web_search_preview",
                    "search_context_size": "high",
                    "user_location": {"type": "approximate", "country": "US"},
                }
            ],
            tool_choice={"type": "web_search_preview"},
            input=prompt,
        )

        citations = []
        seen_urls: set[str] = set()
        position = 1

        for item in response.output:
            if item.type == "message":
                for content in item.content:
                    if content.type == "output_text":
                        for annotation in content.annotations:
                            if (
                                annotation.type == "url_citation"
                                and annotation.url not in seen_urls
                            ):
                                seen_urls.add(annotation.url)
                                # Extract snippet from surrounding text
                                text = content.text
                                start = max(0, annotation.start_index - 50)
                                end = min(len(text), annotation.end_index + 50)
                                snippet = text[start:end].strip()

                                citations.append(
                                    {
                                        "url": annotation.url,
                                        "title": annotation.title or "",
                                        "snippet": snippet,
                                        "position": position,
                                    }
                                )
                                position += 1

        return citations

    except Exception as e:
        logger.error(f"OpenAI search failed for prompt '{prompt[:50]}': {e}")
        return []
