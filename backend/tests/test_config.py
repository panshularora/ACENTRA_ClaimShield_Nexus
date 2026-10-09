import pytest

from claimshield.core.config import Settings


def test_unprefixed_aws_env_aliases(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    for key in (
        "CLAIMSHIELD_AWS_REGION",
        "CLAIMSHIELD_S3_BUCKET",
        "CLAIMSHIELD_S3_INCOMING_PREFIX",
        "CLAIMSHIELD_S3_INPUT_PREFIX",
        "CLAIMSHIELD_S3_PROCESSED_PREFIX",
        "CLAIMSHIELD_S3_RESULTS_PREFIX",
        "CLAIMSHIELD_LAMBDA_FUNCTION",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("AWS_REGION", "ap-south-1")
    monkeypatch.setenv("S3_BUCKET", "claimshield-nexus-data-2026")
    monkeypatch.setenv("S3_INPUT_PREFIX", "incoming/")
    monkeypatch.setenv("S3_PROCESSED_PREFIX", "processed/")
    monkeypatch.setenv("S3_RESULTS_PREFIX", "results/")
    monkeypatch.setenv("LAMBDA_FUNCTION", "claimshield-s3-processor")
    settings = Settings(_env_file=None)
    assert settings.aws_region == "ap-south-1"
    assert settings.s3_bucket == "claimshield-nexus-data-2026"
    assert settings.s3_incoming_prefix == "incoming/"
    assert settings.s3_processed_prefix == "processed/"
    assert settings.s3_results_prefix == "results/"
    assert settings.lambda_function == "claimshield-s3-processor"
    public = settings.aws_public_status()
    assert "internal_token" not in public
    assert public["token_configured"] is False


def test_default_signing_key_refused_outside_demo_mode() -> None:
    with pytest.raises(RuntimeError, match="placeholder"):
        Settings(demo_mode=False, jwt_signing_key="dev-only-change-me").assert_safe_to_start()
    with pytest.raises(RuntimeError, match="32 bytes"):
        Settings(demo_mode=False, jwt_signing_key="short-key").assert_safe_to_start()


def test_demo_mode_and_strong_keys_start() -> None:
    Settings(demo_mode=True, jwt_signing_key="dev-only-change-me").assert_safe_to_start()
    Settings(demo_mode=False, jwt_signing_key="k" * 48).assert_safe_to_start()
