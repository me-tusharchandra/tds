from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    openai_api_key: str = ""
    google_api_key: str = ""
    perplexity_api_key: str = ""
    exa_api_key: str = ""

    # Supabase Python client (REST API via PostgREST)
    # Found in: Project Settings → API
    supabase_url: str = ""  # e.g. https://abc123.supabase.co
    supabase_key: str = ""  # service_role key (server-side, bypasses RLS)

    # Rate limiting
    max_concurrent_engines: int = 4
    max_concurrent_prompts: int = 3

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
