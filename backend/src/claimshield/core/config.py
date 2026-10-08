from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator
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
    cookie_samesite: Literal["lax", "strict", "none"] = "strict"
    # Comma-separated extra browser origins (Vercel, tunnels). Local Vite is always allowed.
    cors_origins: str = ""
    demo_mode: bool = True
    # On serverless, /tmp SQLite is empty each cold start. Seed tiny/7 so the desk is not blank.
    auto_seed_batch: bool = False
    data_profile: str = "tiny"
    evidence_strength_min: float = 0.4
    harm_capacity_share: float = 0.35
    harm_override_level: int = 4
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
    # Shared with Lambda. Empty disables POST /api/v1/aws/ingest. Never log or return this value.
    internal_token: str = ""
    aws_region: str = "ap-south-1"
    s3_bucket: str = "claimshield-nexus-data-2026"
    # Incoming drop prefix. Also accepted as S3_INPUT_PREFIX (hackathon sheet name).
    s3_incoming_prefix: str = "incoming/"
    s3_processed_prefix: str = "processed/"
    s3_results_prefix: str = "results/"
    lambda_function: str = "claimshield-s3-processor"
    # Optional explicit keys for hosts without an instance role (Vercel). Prefer IAM roles.
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    s3_local_dir: Path | None = None
    ingest_max_bytes: int = 52_428_800

    @model_validator(mode="before")
    @classmethod
    def accept_unprefixed_aws_env(cls, data: Any) -> Any:
        """CLAIMSHIELD_* plus the unprefixed names from the AWS run sheet."""
        if not isinstance(data, dict):
            return data
        aliases: dict[str, tuple[str, ...]] = {
            "aws_region": ("AWS_REGION", "CLAIMSHIELD_AWS_REGION"),
            "s3_bucket": ("S3_BUCKET", "CLAIMSHIELD_S3_BUCKET"),
            "s3_incoming_prefix": (
                "S3_INPUT_PREFIX",
                "S3_INCOMING_PREFIX",
                "CLAIMSHIELD_S3_INPUT_PREFIX",
                "CLAIMSHIELD_S3_INCOMING_PREFIX",
            ),
            "s3_processed_prefix": ("S3_PROCESSED_PREFIX", "CLAIMSHIELD_S3_PROCESSED_PREFIX"),
            "s3_results_prefix": ("S3_RESULTS_PREFIX", "CLAIMSHIELD_S3_RESULTS_PREFIX"),
            "lambda_function": ("LAMBDA_FUNCTION", "CLAIMSHIELD_LAMBDA_FUNCTION"),
            "aws_access_key_id": ("AWS_ACCESS_KEY_ID", "CLAIMSHIELD_AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": ("AWS_SECRET_ACCESS_KEY", "CLAIMSHIELD_AWS_SECRET_ACCESS_KEY"),
            "internal_token": ("CLAIMSHIELD_INTERNAL_TOKEN",),
        }
        for field, keys in aliases.items():
            current = data.get(field)
            if current not in (None, ""):
                continue
            for key in keys:
                value = os.environ.get(key)
                if value:
                    data[field] = value
                    break
        return data

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

    def aws_public_status(self) -> dict[str, Any]:
        """Bucket/prefix wiring for the UI. Never includes the internal token or AWS keys."""
        local = self.s3_local_dir is not None
        return {
            "region": self.aws_region,
            "bucket": self.s3_bucket,
            "incoming_prefix": self.s3_incoming_prefix,
            "processed_prefix": self.s3_processed_prefix,
            "results_prefix": self.s3_results_prefix,
            "lambda_function": self.lambda_function,
            "token_configured": bool(self.internal_token),
            "credentials_configured": bool(self.aws_access_key_id and self.aws_secret_access_key) or local,
            "store": "local_dir" if local else "s3",
            "ingest_path": "/api/v1/aws/ingest",
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
