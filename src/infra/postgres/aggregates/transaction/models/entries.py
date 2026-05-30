from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from ....base import PostgresPersistedRecordMixin, mapper_registry


@mapper_registry.mapped
class EntryRecord(PostgresPersistedRecordMixin):
    __tablename__ = "entries"

    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
    )
    ledger_account_id: Mapped[int] = mapped_column(
        ForeignKey("ledger_accounts.id"),
        nullable=False,
    )
    currency_id: Mapped[int] = mapped_column(
        ForeignKey("currencies.id"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(asdecimal=True),
        nullable=False,
    )
    statement_closing_date: Mapped[date | None] = mapped_column(
        Date(),
        nullable=True,
    )
    statement_due_date: Mapped[date | None] = mapped_column(
        Date(),
        nullable=True,
    )
