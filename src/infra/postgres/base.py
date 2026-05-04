from datetime import datetime

from sqlalchemy import Boolean, DateTime, FetchedValue, Identity, Integer, text
from sqlalchemy.orm import Mapped, mapped_column, registry

mapper_registry = registry()
postgres_metadata = mapper_registry.metadata


class PostgresPersistedRecordMixin:
    id: Mapped[int] = mapped_column(
        Integer,
        Identity(),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("TIMEZONE('UTC', CURRENT_TIMESTAMP)"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("TIMEZONE('UTC', CURRENT_TIMESTAMP)"),
        server_onupdate=FetchedValue(),
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("FALSE"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        server_onupdate=FetchedValue(),
    )
