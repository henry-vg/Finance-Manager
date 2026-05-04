import base64
import binascii
import hashlib
import hmac
import os
from dataclasses import dataclass

from src.core.ports.output.password_hasher_output_port import PasswordHasherOutputPort

_ALGORITHM_NAME = "scrypt"
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 64
_SALT_LENGTH = 16


class ScryptPasswordHasher(PasswordHasherOutputPort):
    def hash_password(
        self,
        password: str,
    ) -> str:
        salt = os.urandom(_SALT_LENGTH)
        password_hash = hashlib.scrypt(
            password=password.encode("utf-8"),
            salt=salt,
            n=_SCRYPT_N,
            r=_SCRYPT_R,
            p=_SCRYPT_P,
            dklen=_SCRYPT_DKLEN,
        )

        salt_encoded = base64.b64encode(salt).decode("utf-8")
        password_hash_encoded = base64.b64encode(password_hash).decode("utf-8")

        return (
            f"{_ALGORITHM_NAME}"
            f"$n={_SCRYPT_N}"
            f"$r={_SCRYPT_R}"
            f"$p={_SCRYPT_P}"
            f"$dklen={_SCRYPT_DKLEN}"
            f"${salt_encoded}"
            f"${password_hash_encoded}"
        )

    def verify_password(
        self,
        password: str,
        password_hash: str,
    ) -> bool:
        parsed_hash = self._parse_password_hash(password_hash)

        if parsed_hash is None:
            return False

        try:
            derived_hash = hashlib.scrypt(
                password=password.encode("utf-8"),
                salt=parsed_hash.salt,
                n=parsed_hash.n,
                r=parsed_hash.r,
                p=parsed_hash.p,
                dklen=parsed_hash.dklen,
            )
        except ValueError:
            return False

        return hmac.compare_digest(derived_hash, parsed_hash.password_hash)

    def _parse_password_hash(
        self,
        password_hash: str,
    ) -> "_ParsedScryptHash | None":
        parts = password_hash.split("$")

        if len(parts) != 7:
            return None

        algorithm_name, n_part, r_part, p_part, dklen_part, salt_part, hash_part = parts

        if algorithm_name != _ALGORITHM_NAME:
            return None

        try:
            n = self._parse_parameter(n_part, expected_name="n")
            r = self._parse_parameter(r_part, expected_name="r")
            p = self._parse_parameter(p_part, expected_name="p")
            dklen = self._parse_parameter(dklen_part, expected_name="dklen")
            salt = base64.b64decode(salt_part.encode("utf-8"), validate=True)
            derived_hash = base64.b64decode(hash_part.encode("utf-8"), validate=True)
        except (binascii.Error, ValueError):
            return None

        if not salt or not derived_hash:
            return None

        if len(derived_hash) != dklen:
            return None

        return _ParsedScryptHash(
            n=n,
            r=r,
            p=p,
            dklen=dklen,
            salt=salt,
            password_hash=derived_hash,
        )

    def _parse_parameter(
        self,
        part: str,
        *,
        expected_name: str,
    ) -> int:
        name, separator, value = part.partition("=")

        if separator != "=" or name != expected_name:
            raise ValueError("Invalid scrypt parameter")

        parsed_value = int(value)

        if parsed_value <= 0:
            raise ValueError("Scrypt parameter must be positive")

        return parsed_value


@dataclass(frozen=True)
class _ParsedScryptHash:
    n: int
    r: int
    p: int
    dklen: int
    salt: bytes
    password_hash: bytes
