from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.domain.ledger_account import Currency
from src.core.domain.transaction import TransactionStatus
from src.infra.postgres.aggregates.ledger_account.models.ledger_accounts import (
    currency_enum,
)

from ....base import PostgresPersistedRecordMixin, mapper_registry


def _enum_values(enum_cls: type[TransactionStatus]) -> list[str]:
    return [member.name for member in enum_cls]


transaction_status_enum = Enum(
    TransactionStatus,
    name="transaction_status_enum",
    values_callable=_enum_values,
)


@mapper_registry.mapped
class TransactionRecord(PostgresPersistedRecordMixin):
    __tablename__ = "transactions"

    effective_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(length=255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text(),
        nullable=True,
    )
    status: Mapped[TransactionStatus] = mapped_column(
        transaction_status_enum,
        nullable=False,
    )
    currency: Mapped[Currency] = mapped_column(
        currency_enum,
        nullable=False,
    )
