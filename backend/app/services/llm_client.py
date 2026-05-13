"""Shared LLM client selector.

Both internal helpers (brand_extractor, competitor_discovery, prompt_generator)
and the search engines need to pick a provider at call time. Centralising the
selection avoids each call site re-implementing the same OpenRouter-or-native
precedence rule (and forgetting it — which is exactly how we ended up
hammering OpenRouter with empty Authorization headers).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class LLMClient:
    client: AsyncOpenAI
    model: str
    provider: str  # "openrouter" or "openai"
    supports_web_search: bool = False


def get_llm(*, kind: str = "mini") -> LLMClient | None:
    """Pick a general-purpose LLM client.

    kind="mini" for cheap/fast tasks (brand summary, prompt gen, extraction).
    kind="main" for higher-quality tasks. Returns None when no credentials
    are configured — callers must handle that and fall back gracefully.
    """
    settings = get_settings()

    if settings.openrouter_api_key:
        client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
        model = "openai/gpt-4o-mini" if kind == "mini" else "openai/gpt-4o"
        return LLMClient(client=client, model=model, provider="openrouter")

    if settings.openai_api_key:
        client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        model = "gpt-4o-mini" if kind == "mini" else "gpt-4o"
        return LLMClient(client=client, model=model, provider="openai")

    return None


def get_search_llm() -> LLMClient | None:
    """Pick an LLM client that can perform live web search.

    OpenRouter path uses perplexity/sonar (native web search).
    OpenAI direct path uses gpt-4o-search-preview with web_search_options.
    """
    settings = get_settings()

    if settings.openrouter_api_key:
        client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
        return LLMClient(
            client=client,
            model="perplexity/sonar",
            provider="openrouter",
            supports_web_search=True,
        )

    if settings.openai_api_key:
        client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        return LLMClient(
            client=client,
            model="gpt-4o-search-preview",
            provider="openai",
            supports_web_search=True,
        )

    return None
