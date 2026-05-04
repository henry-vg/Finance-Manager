from datetime import date

from sqlalchemy import Date, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ....base import PostgresPersistedRecordMixin, mapper_registry

USER_EMAIL_UNIQUE_CONSTRAINT_NAME = "uq_users_email"


@mapper_registry.mapped
class UserRecord(PostgresPersistedRecordMixin):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint(
            "email",
            name=USER_EMAIL_UNIQUE_CONSTRAINT_NAME,
        ),
    )
    first_name: Mapped[str] = mapped_column(
        String(length=255),
        nullable=False,
    )
    last_name: Mapped[str] = mapped_column(
        String(length=255),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(length=255),
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(length=255),
        nullable=False,
    )
    birth_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
