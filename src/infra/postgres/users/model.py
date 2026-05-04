from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import PostgresPersistedRecordMixin, mapper_registry


@mapper_registry.mapped
class UserRecord(PostgresPersistedRecordMixin):
    __tablename__ = "users"
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
        unique=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(length=255),
        nullable=False,
    )
    birth_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
