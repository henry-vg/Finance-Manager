from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.domain.ledger_account import (
    LedgerAccountInstrumentKind,
    LedgerAccountType,
)

from ....base import PostgresPersistedRecordMixin, mapper_registry


def _enum_values(
    enum_cls: type[LedgerAccountType] | type[LedgerAccountInstrumentKind],
) -> list[str]:
    return [member.name for member in enum_cls]


ledger_account_type_enum = Enum(
    LedgerAccountType,
    name="ledger_account_type_enum",
    values_callable=_enum_values,
)

ledger_account_instrument_kind_enum = Enum(
    LedgerAccountInstrumentKind,
    name="ledger_account_instrument_kind_enum",
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
    instrument_kind: Mapped[LedgerAccountInstrumentKind | None] = mapped_column(
        ledger_account_instrument_kind_enum,
        nullable=True,
    )
