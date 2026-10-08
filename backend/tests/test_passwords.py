from claimshield.auth.passwords import hash_password, verify_password


def test_argon2id_hash_is_not_plaintext_and_verifies() -> None:
    password = "demo-pass-investigator-1"
    hashed = hash_password(password)
    assert hashed != password
    assert hashed.startswith("$argon2")
    assert verify_password(password, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_same_password_produces_distinct_salts() -> None:
    password = "same-secret"
    first = hash_password(password)
    second = hash_password(password)
    assert first != second
    assert verify_password(password, first)
    assert verify_password(password, second)
