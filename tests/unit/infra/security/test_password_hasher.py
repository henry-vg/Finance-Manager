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


def test_verify_password_rejects_hash_with_invalid_parameter_name() -> None:
    password_hasher = ScryptPasswordHasher()
    password_hash = password_hasher.hash_password("plain-password")

    invalid_hash = password_hash.replace("n=16384", "x=16384", 1)

    assert (
        password_hasher.verify_password(
            password="plain-password",
            password_hash=invalid_hash,
        )
        is False
    )


def test_verify_password_rejects_hash_with_non_positive_parameter() -> None:
    password_hasher = ScryptPasswordHasher()
    password_hash = password_hasher.hash_password("plain-password")

    invalid_hash = password_hash.replace("n=16384", "n=0", 1)

    assert (
        password_hasher.verify_password(
            password="plain-password",
            password_hash=invalid_hash,
        )
        is False
    )


def test_verify_password_rejects_hash_with_invalid_scrypt_work_factor() -> None:
    password_hasher = ScryptPasswordHasher()
    password_hash = password_hasher.hash_password("plain-password")

    invalid_hash = password_hash.replace("n=16384", "n=3", 1)

    assert (
        password_hasher.verify_password(
            password="plain-password",
            password_hash=invalid_hash,
        )
        is False
    )


def test_verify_password_rejects_hash_with_invalid_algorithm_name() -> None:
    password_hasher = ScryptPasswordHasher()
    password_hash = password_hasher.hash_password("plain-password")

    invalid_hash = password_hash.replace("scrypt", "bcrypt", 1)

    assert (
        password_hasher.verify_password(
            password="plain-password",
            password_hash=invalid_hash,
        )
        is False
    )


def test_verify_password_rejects_hash_with_empty_salt() -> None:
    password_hasher = ScryptPasswordHasher()
    password_hash = password_hasher.hash_password("plain-password")
    algorithm_name, n_part, r_part, p_part, dklen_part, _, hash_part = (
        password_hash.split("$")
    )
    invalid_hash = "$".join(
        [algorithm_name, n_part, r_part, p_part, dklen_part, "", hash_part],
    )

    assert (
        password_hasher.verify_password(
            password="plain-password",
            password_hash=invalid_hash,
        )
        is False
    )
