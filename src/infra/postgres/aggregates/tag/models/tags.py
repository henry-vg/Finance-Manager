from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ....base import PostgresPersistedRecordMixin, mapper_registry


@mapper_registry.mapped
class TagRecord(PostgresPersistedRecordMixin):
    __tablename__ = "tags"

    title: Mapped[str] = mapped_column(
        String(length=255),
        nullable=False,
    )
