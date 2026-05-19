from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ....base import mapper_registry


@mapper_registry.mapped
class EntryTagRecord:
    __tablename__ = "entry_tags"

    entry_id: Mapped[int] = mapped_column(
        ForeignKey("entries.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id"),
        primary_key=True,
    )
