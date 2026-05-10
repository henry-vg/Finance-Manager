from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.domain.ledger_account import (
    Currency,
    LedgerAccountKind,
    LedgerAccountType,
)

from ....base import PostgresPersistedRecordMixin, mapper_registry


def _enum_values(
    enum_cls: type[Currency] | type[LedgerAccountType] | type[LedgerAccountKind],
) -> list[str]:
    return [member.name for member in enum_cls]


ledger_account_type_enum = Enum(
    LedgerAccountType,
    name="ledger_account_type_enum",
    values_callable=_enum_values,
)

ledger_account_kind_enum = Enum(
    LedgerAccountKind,
    name="ledger_account_kind_enum",
    values_callable=_enum_values,
)

currency_enum = Enum(
    Currency,
    name="currency_enum",
    values_callable=_enum_values,
)


@mapper_registry.mapped
class LedgerAccountRecord(PostgresPersistedRecordMixin):
    __tablename__ = "ledger_accounts"

    title: Mapped[str] = mapped_column(
        String(length=255),
        nullable=False,
    )
    type: Mapped[LedgerAccountType] = mapped_column(
        ledger_account_type_enum,
        nullable=False,
    )
    kind: Mapped[LedgerAccountKind] = mapped_column(
        ledger_account_kind_enum,
        nullable=False,
    )
    currency: Mapped[Currency] = mapped_column(
        currency_enum,
        nullable=False,
    )
