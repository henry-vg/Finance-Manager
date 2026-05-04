import re

from src.infra.security import ScryptPasswordHasher


def test_hash_password_returns_self_describing_scrypt_format() -> None:
    password_hasher = ScryptPasswordHasher()

    password_hash = password_hasher.hash_password("plain-password")

    assert (
        re.fullmatch(
            r"scrypt\$n=16384\$r=8\$p=1\$dklen=64\$[^$]+\$[^$]+",
            password_hash,
        )
        is not None
    )


def test_verify_password_returns_true_for_matching_password() -> None:
    password_hasher = ScryptPasswordHasher()
    password_hash = password_hasher.hash_password("plain-password")

    assert (
        password_hasher.verify_password(
            password="plain-password",
            password_hash=password_hash,
        )
        is True
    )


def test_verify_password_returns_false_for_non_matching_password() -> None:
    password_hasher = ScryptPasswordHasher()
    password_hash = password_hasher.hash_password("plain-password")

    assert (
        password_hasher.verify_password(
            password="wrong-password",
            password_hash=password_hash,
        )
        is False
    )


def test_verify_password_rejects_legacy_hash_format() -> None:
    password_hasher = ScryptPasswordHasher()

    assert (
        password_hasher.verify_password(
            password="plain-password",
            password_hash="scrypt$c2FsdA==$aGFzaA==",
        )
        is False
    )


def test_verify_password_rejects_malformed_hash_payload() -> None:
    password_hasher = ScryptPasswordHasher()

    assert (
        password_hasher.verify_password(
            password="plain-password",
            password_hash="scrypt$n=16384$r=8$p=1$dklen=64$not-base64$still-not-base64",
        )
        is False
    )


def test_verify_password_rejects_hash_with_inconsistent_dklen() -> None:
    password_hasher = ScryptPasswordHasher()
    password_hash = password_hasher.hash_password("plain-password")

    inconsistent_hash = password_hash.replace("dklen=64", "dklen=32", 1)

    assert (
        password_hasher.verify_password(
            password="plain-password",
            password_hash=inconsistent_hash,
        )
        is False
    )
