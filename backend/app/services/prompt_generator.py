import logging

from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)

TEMPLATE_PROMPTS = [
    ("best_tools", "What are the best {category} tools in 2025?"),
    ("alternatives", "What are the best alternatives to {brand}?"),
    ("comparison", "Compare the top {category} platforms"),
    ("recommendation", "Which {category} software would you recommend for a business?"),
    ("review", "What is the best {category} solution and why?"),
    ("top_list", "Top 10 {category} companies"),
    ("vs", "What are the pros and cons of {brand} vs competitors?"),
    ("use_case", "Best {category} for small businesses"),
]


async def generate_prompts(
    brand_name: str,
    brand_description: str,
    num_prompts: int = 8,
) -> list[dict]:
    """Generate search prompts for AI engines.

    Returns list of dicts with keys: prompt_text, category
    """
    settings = get_settings()

    # Use LLM to infer category from brand description
    category = await _infer_category(brand_name, brand_description, settings)

    prompts = []
    for cat, template in TEMPLATE_PROMPTS[:num_prompts]:
        prompt_text = template.format(brand=brand_name, category=category)
        prompts.append({"prompt_text": prompt_text, "category": cat})

    return prompts


async def _infer_category(
    brand_name: str, brand_description: str, settings
) -> str:
    """Use OpenAI to infer the brand's category/industry."""
    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a market analyst. Given a brand name and description, respond with ONLY the product category or industry in 2-4 words. Examples: 'project management', 'email marketing', 'CRM software', 'cloud storage'. No punctuation.",
                },
                {
                    "role": "user",
                    "content": f"Brand: {brand_name}\nDescription: {brand_description}",
                },
            ],
            max_tokens=20,
            temperature=0,
        )
        category = response.choices[0].message.content.strip().lower()
        return category
    except Exception as e:
        logger.warning(f"Category inference failed: {e}, using brand name")
        return brand_name.lower()
