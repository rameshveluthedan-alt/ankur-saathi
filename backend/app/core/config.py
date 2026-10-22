"""
Ankur Saathi — Configuration
All settings from environment variables with sensible defaults for local dev.
"""

from functools import lru_cache
from urllib.parse import quote

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App
    app_name: str = "Ankur Saathi"
    app_version: str = "0.1.0"
    debug: bool = True
    
    # Database
    # Either DATABASE_URL, or the parts the scripts also read from this same .env file (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME).
    # If DATABASE_URL is empty the URL is built from the parts, with the password percent-encoded (a password may contain @ : / #).
    database_url: str = ""
    db_host: str = ""
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
    
    # Embedding API (for L2 semantic search)
    embedding_api_key: str = ""
    embedding_api_url: str = "https://api.openai.com/v1/embeddings"
    embedding_model: str = "text-embedding-3-small"
    
    # AI budget (docs/AI_BUDGET.md). The hackathon credits are a fixed pool that must last through evaluation, so every call is metered and capped
    ai_enabled: bool = True                     # false = no calls at all (recorded sample plans are still served)
    ai_allocation_usd: float = 500.0            # the credit the organisers gave (15 Oct 2026). Raise it if the extra credit is granted
    ai_spend_offset_usd: float = 3.0            # spent before the meter existed (an estimate: plans generated while developing)
    ai_credit_expires: str = "2026-11-20"       # keys stop working after this date
    ai_reserve_usd: float = 250.0               # kept back for evaluators: development cannot spend into it
    ai_reserve_from: str = "2026-11-01"         # from this date the reserve is released (the evaluation window)
    ai_final_margin_usd: float = 10.0           # never spend the last few dollars
    ai_cap_global_daily_usd: float = 20.0       # the kill switch: all users together, per day (10 evaluation days x $20 stays inside the $240 evaluation budget)
    ai_cap_school_daily_usd: float = 10.0
    ai_cap_teacher_daily_usd: float = 3.0
    ai_cap_shared_demo_daily_usd: float = 8.0   # a shared demo account (fixed PIN) is used by many reviewers
    ai_price_input_per_mtok: float = 2.0        # USD per million input tokens. CHECK Anthropic's pricing page for the model you use
    ai_price_output_per_mtok: float = 10.0      # USD per million output tokens (thinking tokens count as output)
    ai_timezone: str = "Asia/Kolkata"           # a "day" for the daily caps
    sample_plans_dir: str = ""                  # recorded plans served when the AI limit is reached; default db/seeds/sample_plans

    # Sign-in (docs/AUTH.md)
    auth_mode: str = "enforce"          # "enforce" for everything real. "off" exists only so automated tests of other features can skip sign-in
    session_secret: str = ""            # REQUIRED when debug is false. A long random string; changing it signs everyone out
    session_hours: int = 12             # how long a sign-in lasts
    pin_hash_iterations: int = 600_000  # PBKDF2 cost; the count is stored with each hash, so it can be raised later

    # CORS (allow PWA origin)
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173", "https://*.ankursaathi.in"]
    
    # Plan generation
    anchor_duration_minutes: int = 10
    setup_duration_minutes: int = 2
    reteach_duration_minutes: int = 5
    cfu_enabled: bool = True                    # check-for-understanding show-me questions in every lesson (docs/CFU.md). false = plans exactly as before
    transition_duration_minutes: int = 2
    default_teaching_minutes: int = 90
    
    # Photo pipeline
    max_image_size_bytes: int = 15_000_000  # raw upload limit; the app shrinks photos first and the server re-compresses before Vision
    max_images_per_batch: int = 6
    
    # State (for curriculum plan lookup)
    default_state_id: str = "mp"
    
    # A line in .env that the app does not use (the scripts' DB_* parts, or anything else) is ignored, not an error:
    # the default is to REFUSE it, which stops the whole server from starting.
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @model_validator(mode="after")
    def _build_database_url(self):
        if not self.database_url:
            if self.db_host or self.db_password:
                auth = quote(self.db_user, safe="") + (":" + quote(self.db_password, safe="") if self.db_password else "")
                self.database_url = f"postgresql://{auth}@{self.db_host or 'localhost'}:{self.db_port}/{self.db_name}"
            else:
                self.database_url = "postgresql://postgres@localhost/ankur_saathi"
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
