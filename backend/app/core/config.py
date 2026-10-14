"""
Ankur Saathi — Configuration
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Ankur Saathi"
    app_version: str = "0.1.0"
    debug: bool = True

    # Database (explicit params — URL parsing fails on some Windows setups)
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = ""
    db_name: str = "ankur_saathi"
    db_pool_min: int = 2
    db_pool_max: int = 10

    # Claude API
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"
    claude_vision_model: str = "claude-sonnet-4-6"
    claude_max_tokens: int = 8000

    # Embedding API
    embedding_api_key: str = ""
    embedding_api_url: str = "https://api.openai.com/v1/embeddings"
    embedding_model: str = "text-embedding-3-small"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Plan generation
    anchor_duration_minutes: int = 10
    setup_duration_minutes: int = 2
    reteach_duration_minutes: int = 5
    transition_duration_minutes: int = 2
    default_teaching_minutes: int = 90

    # Photo pipeline
    max_image_size_bytes: int = 2_000_000
    max_images_per_batch: int = 6

    # State
    default_state_id: str = "mp"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()