import base64
import hashlib
import os

from src.core.ports.output.password_hasher_output_port import PasswordHasherOutputPort


class ScryptPasswordHasher(PasswordHasherOutputPort):
    def hash_password(
        self,
        password: str,
    ) -> str:
        salt = os.urandom(16)
        password_hash = hashlib.scrypt(
            password=password.encode("utf-8"),
            salt=salt,
            n=2**14,
            r=8,
            p=1,
        )

        salt_encoded = base64.b64encode(salt).decode("utf-8")
        password_hash_encoded = base64.b64encode(password_hash).decode("utf-8")

        return f"scrypt${salt_encoded}${password_hash_encoded}"
