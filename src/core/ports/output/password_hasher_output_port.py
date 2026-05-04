from typing import Protocol


class PasswordHasherOutputPort(Protocol):
    def hash_password(
        self,
        password: str,
    ) -> str: ...
