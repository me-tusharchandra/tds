import logging

from app.services.cost_tracker import CostTracker, extract_cost_from_response
from app.services.llm_client import get_llm

logger = logging.getLogger(__name__)


async def generate_prompts(
    brand_name: str,
    brand_description: str,
    competitors: list[dict] | None = None,
    num_prompts: int = 8,
    cost_tracker: CostTracker | None = None,
) -> list[dict]:
    """Generate category-level discovery prompts — no brand names.

    The goal is to test whether AI engines organically surface the brand
    when a user asks a natural category/use-case question.
    """
    llm = get_llm(kind="mini")
    if llm is None:
        logger.warning(
            "Prompt generator: no LLM credentials — falling back to templates"
        )
        return _template_prompts(brand_description or brand_name, num_prompts)

    try:
        response = await llm.client.chat.completions.create(
            model=llm.model,
            messages=[
                {
                    "role": "system",
                    "content": """You generate hyper-specific search prompts to test whether AI engines organically surface a given brand.

You will receive the brand's description, its niche, and its top competitors. Use ALL of this context to craft prompts that sound like a real person talking to ChatGPT or Perplexity — specific pain points, real use-cases, comparison angles, buyer personas.

CRITICAL RULES:
- NEVER include any brand names or company names in the prompts
- Prompts must be deeply specific to this exact brand's niche and value proposition — not generic category queries
- Imagine the brand's ideal customer: what would THEY ask an AI chatbot right before buying?
- Reference real pain points, workflows, team sizes, industries, budgets where relevant
- Mix intent types: research, buying, head-to-head comparison, migration, use-case-specific
- Each prompt should feel like a unique, natural question — not a template with words swapped
- Vary specificity: some broad discovery, some razor-sharp ("for a 20-person remote team", "under $50/month", "with Slack integration")

Output format: One prompt per line, prefixed with category in brackets.
Categories: discovery, recommendation, use_case, comparison, buying, specific, evaluation, industry""",
                },
                {
                    "role": "user",
                    "content": f"""Brand: {brand_name}
Description: {brand_description or "N/A"}
Top competitors: {", ".join(c.get("name", "") for c in (competitors or [])[:5]) or "N/A"}

Generate {num_prompts} highly personalized discovery prompts. Make them sound like real questions a potential customer in this exact niche would ask an AI assistant. No brand names in the output.""",
                },
            ],
            max_tokens=1000,
            temperature=0.7,
        )

        if cost_tracker:
            pt, ct, cost = extract_cost_from_response(response)
            cost_tracker.record("prompt_gen", llm.model, pt, ct, cost)

        raw = response.choices[0].message.content or ""
        prompts = []
        for line in raw.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("["):
                bracket_end = line.find("]")
                if bracket_end > 0:
                    category = line[1:bracket_end].strip()
                    prompt_text = line[bracket_end + 1 :].strip()
                    if prompt_text:
                        prompts.append(
                            {"prompt_text": prompt_text, "category": category}
                        )
                        continue
            prompts.append({"prompt_text": line, "category": "general"})

        if prompts:
            return prompts[:num_prompts]

    except Exception as e:
        logger.warning(f"LLM prompt generation failed: {e}, using templates")

    # Fallback: infer niche from description and use templates
    return _template_prompts(brand_description or brand_name, num_prompts)


def _template_prompts(niche: str, num_prompts: int) -> list[dict]:
    """Fallback template-based prompts — no brand names, category-level only."""
    short_niche = niche[:80]
    prompts = [
        {"prompt_text": f"What are the best {short_niche} tools in 2025?", "category": "discovery"},
        {"prompt_text": f"Recommend a good {short_niche} platform for small businesses", "category": "recommendation"},
        {"prompt_text": f"Top rated {short_niche} solutions", "category": "comparison"},
        {"prompt_text": f"What should I look for when choosing a {short_niche} tool?", "category": "evaluation"},
        {"prompt_text": f"Best {short_niche} software for startups", "category": "use_case"},
        {"prompt_text": f"Which {short_niche} platforms have the best reviews?", "category": "buying"},
        {"prompt_text": f"How do I choose between different {short_niche} providers?", "category": "comparison"},
        {"prompt_text": f"Most popular {short_niche} tools used by companies today", "category": "discovery"},
    ]
    return prompts[:num_prompts]
