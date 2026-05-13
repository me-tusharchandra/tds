from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # OpenRouter - single API key for all LLMs (preferred when set)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Direct provider keys - used as fallback when OpenRouter key is empty
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    gemini_api_key: str = ""

    # Exa AI - direct API (not an LLM, separate service)
    exa_api_key: str = ""

    # Supabase Python client (REST API via PostgREST)
    supabase_url: str = ""
    supabase_key: str = ""

    # Rate limiting
    max_concurrent_engines: int = 4
    max_concurrent_prompts: int = 3

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
