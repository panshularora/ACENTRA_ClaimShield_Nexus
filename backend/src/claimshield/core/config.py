from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_JWT_SIGNING_KEY = "dev-only-change-me"
PLACEHOLDER_JWT_KEYS = frozenset({DEFAULT_JWT_SIGNING_KEY, "change-me-in-compose"})
MIN_JWT_KEY_BYTES = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CLAIMSHIELD_",
        env_file=".env",
        extra="ignore",
    )

    database_url: str = "sqlite+pysqlite:///./claimshield.db"
    jwt_signing_key: str = Field(default=DEFAULT_JWT_SIGNING_KEY)
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
    # Trained risk-model artifact; defaults to data_dir/models/risk_model.json when unset.
    risk_model_path: Path | None = None
    internal_token: str = ""
    aws_region: str = "ap-south-1"
    s3_bucket: str = "claimshield-nexus-data-2026"
    s3_incoming_prefix: str = "incoming/"
    s3_processed_prefix: str = "processed/"
    s3_results_prefix: str = "results/"
    s3_local_dir: Path | None = None
    ingest_max_bytes: int = 52_428_800

    def startup_problems(self) -> list[str]:
        """Configuration that is only acceptable for a local demo."""
        problems: list[str] = []
        if self.jwt_signing_key in PLACEHOLDER_JWT_KEYS:
            problems.append("CLAIMSHIELD_JWT_SIGNING_KEY is a placeholder value")
        elif len(self.jwt_signing_key.encode()) < MIN_JWT_KEY_BYTES:
            problems.append(f"CLAIMSHIELD_JWT_SIGNING_KEY must be at least {MIN_JWT_KEY_BYTES} bytes")
        return problems

    def assert_safe_to_start(self) -> None:
        """Refuse to serve outside demo mode with a guessable signing key."""
        problems = self.startup_problems()
        if problems and not self.demo_mode:
            raise RuntimeError("refusing to start outside demo mode: " + "; ".join(problems))

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
