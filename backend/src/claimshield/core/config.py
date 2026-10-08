from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CLAIMSHIELD_",
        env_file=".env",
        extra="ignore",
    )

    database_url: str = "sqlite+pysqlite:///./claimshield.db"
    jwt_signing_key: str = Field(default="dev-only-change-me")
    jwt_access_minutes: int = 15
    refresh_hours: int = 8
    cookie_secure: bool = False
    cookie_samesite: str = "strict"
    demo_mode: bool = True
    data_profile: str = "tiny"
    evidence_strength_min: float = 0.4
    harm_capacity_share: float = 0.35
    harm_override_level: int = 4
    harm_lambda: float = 250.0
    screening_days: int = 45
    max_queue_slots: int = 20
    default_member_weight: float = 1.0
    default_recovery_rate: float = 0.5
    batch_reject_stop_pct: float = 5.0
    llm_base_url: str = "https://api.x.ai/v1"
    llm_api_key: str = ""
    llm_model: str = "grok-4.7"
    data_dir: Path = Path(__file__).resolve().parents[4] / "data"

    @property
    def access_cookie_name(self) -> str:
        return "__Host-access" if self.cookie_secure else "cs_access"

    @property
    def refresh_cookie_name(self) -> str:
        return "__Host-refresh" if self.cookie_secure else "cs_refresh"

    @property
    def csrf_cookie_name(self) -> str:
        return "cs_csrf"


@lru_cache
def get_settings() -> Settings:
    return Settings()
