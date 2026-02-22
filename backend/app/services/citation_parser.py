"""Shared citation extraction from OpenRouter responses."""

from dataclasses import dataclass, field


@dataclass
class SearchResult:
    """Container for search results: citations + the raw LLM response text."""

    citations: list[dict] = field(default_factory=list)
    response_text: str = ""


def extract_citations_from_response(response) -> list[dict]:
    """Extract citations from an OpenRouter response.

    Handles both:
    - annotations (OpenAI/Gemini via :online)
    - top-level citations (Perplexity native)

    Returns list of dicts with keys: url, title, snippet, position
    """
    citations = []
    seen_urls: set[str] = set()
    position = 1
    content = response.choices[0].message.content or ""
    message = response.choices[0].message

    # Method 1: Perplexity-style top-level citations
    raw = response.model_extra or {}
    citation_urls = raw.get("citations", [])
    for url in citation_urls:
        if url and url not in seen_urls:
            seen_urls.add(url)
            citations.append(
                {
                    "url": url,
                    "title": "",
                    "snippet": content[:200] if position == 1 else "",
                    "position": position,
                }
            )
            position += 1

    # Method 2: OpenRouter annotations (url_citation format)
    annotations = getattr(message, "annotations", None) or []
    for ann in annotations:
        url = None
        title = ""
        ann_snippet = ""

        if isinstance(ann, dict):
            if ann.get("type") == "url_citation":
                citation_data = ann.get("url_citation", ann)
                url = citation_data.get("url")
                title = citation_data.get("title", "")
                ann_snippet = citation_data.get("content", "")
            elif ann.get("url"):
                url = ann["url"]
                title = ann.get("title", "")
        else:
            if getattr(ann, "type", None) == "url_citation":
                citation_obj = getattr(ann, "url_citation", ann)
                url = getattr(citation_obj, "url", None)
                title = getattr(citation_obj, "title", "")
                ann_snippet = getattr(citation_obj, "content", "")

        if url and url not in seen_urls:
            seen_urls.add(url)
            citations.append(
                {
                    "url": url,
                    "title": title,
                    "snippet": ann_snippet or content[:200],
                    "position": position,
                }
            )
            position += 1

    return citations
