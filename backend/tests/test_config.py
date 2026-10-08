import pytest

from claimshield.core.config import Settings


def test_default_signing_key_refused_outside_demo_mode() -> None:
    with pytest.raises(RuntimeError, match="placeholder"):
        Settings(demo_mode=False, jwt_signing_key="dev-only-change-me").assert_safe_to_start()
    with pytest.raises(RuntimeError, match="32 bytes"):
        Settings(demo_mode=False, jwt_signing_key="short-key").assert_safe_to_start()


def test_demo_mode_and_strong_keys_start() -> None:
    Settings(demo_mode=True, jwt_signing_key="dev-only-change-me").assert_safe_to_start()
    Settings(demo_mode=False, jwt_signing_key="k" * 48).assert_safe_to_start()
