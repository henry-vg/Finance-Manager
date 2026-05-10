from datetime import date

from sqlalchemy import Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ....base import PostgresPersistedRecordMixin, mapper_registry


@mapper_registry.mapped
class StatementCycleRecord(PostgresPersistedRecordMixin):
    __tablename__ = "statement_cycles"

    ledger_account_id: Mapped[int] = mapped_column(
        ForeignKey("ledger_accounts.id"),
        nullable=False,
    )
    cycle_start: Mapped[date] = mapped_column(
        Date(),
        nullable=False,
    )
    cycle_end: Mapped[date] = mapped_column(
        Date(),
        nullable=False,
    )
    closing_date: Mapped[date] = mapped_column(
        Date(),
        nullable=False,
    )
    due_date: Mapped[date] = mapped_column(
        Date(),
        nullable=False,
    )
