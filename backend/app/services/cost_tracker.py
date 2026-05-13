"""Track API costs across an analysis run."""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Fallback per-call estimates when the provider doesn't return cost
FALLBACK_COSTS = {
    # OpenRouter-prefixed models
    "openai/gpt-4o": 0.006,
    "google/gemini-2.0-flash-001": 0.001,
    "perplexity/sonar": 0.005,
    "openai/gpt-4o-mini": 0.001,
    # Native (direct provider) models
    "gpt-4o-search-preview": 0.012,  # $10/1K calls + token costs
    "gemini-2.5-flash": 0.0,  # free tier
    "web_search_plugin": 0.004,
    "exa_search": 0.005,
    "exa_find_similar": 0.005,
    "exa_get_contents": 0.001,
}


@dataclass
class CostEntry:
    service: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0


@dataclass
class CostTracker:
    entries: list[CostEntry] = field(default_factory=list)

    def record(
        self,
        service: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost: float = 0.0,
    ) -> None:
        if cost == 0.0 and model in FALLBACK_COSTS:
            cost = FALLBACK_COSTS[model]
            if "web" in service.lower() or "online" in model:
                cost += FALLBACK_COSTS["web_search_plugin"]

        self.entries.append(
            CostEntry(
                service=service,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=cost,
            )
        )

    def record_exa(self, operation: str) -> None:
        cost = FALLBACK_COSTS.get(f"exa_{operation}", 0.005)
        self.entries.append(
            CostEntry(service="exa", model=f"exa_{operation}", cost=cost)
        )

    @property
    def total_cost(self) -> float:
        return sum(e.cost for e in self.entries)

    @property
    def total_prompt_tokens(self) -> int:
        return sum(e.prompt_tokens for e in self.entries)

    @property
    def total_completion_tokens(self) -> int:
        return sum(e.completion_tokens for e in self.entries)

    def cost_by_service(self) -> dict[str, float]:
        costs: dict[str, float] = {}
        for e in self.entries:
            costs[e.service] = costs.get(e.service, 0) + e.cost
        return costs

    def log_summary(self, analysis_id: str) -> None:
        by_service = self.cost_by_service()
        total = self.total_cost

        logger.info(f"[{analysis_id}] === COST SUMMARY ===")
        logger.info(
            f"[{analysis_id}] Tokens: {self.total_prompt_tokens:,} prompt + "
            f"{self.total_completion_tokens:,} completion"
        )
        for service, cost in sorted(by_service.items()):
            count = sum(1 for e in self.entries if e.service == service)
            logger.info(
                f"[{analysis_id}]   {service}: ${cost:.4f} ({count} calls)"
            )
        logger.info(f"[{analysis_id}] TOTAL COST: ${total:.4f}")
        logger.info(f"[{analysis_id}] ====================")


def extract_cost_from_response(response) -> tuple[int, int, float]:
    """Extract token counts and cost from an OpenRouter response."""
    usage = getattr(response, "usage", None)
    if not usage:
        return 0, 0, 0.0

    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    cost = getattr(usage, "cost", 0.0) or 0.0

    # cost might also be in model_extra
    if cost == 0.0:
        extra = getattr(response, "model_extra", {}) or {}
        usage_extra = extra.get("usage", {})
        if isinstance(usage_extra, dict):
            cost = usage_extra.get("cost", 0.0) or 0.0

    return prompt_tokens, completion_tokens, float(cost)
