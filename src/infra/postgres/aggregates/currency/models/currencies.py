from sqlalchemy import CheckConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ....base import PostgresPersistedRecordMixin, mapper_registry

CURRENCY_ISO_CODE_UNIQUE_CONSTRAINT_NAME = "uq_currencies_iso_code"


@mapper_registry.mapped
class CurrencyRecord(PostgresPersistedRecordMixin):
    __tablename__ = "currencies"
    __table_args__ = (
        UniqueConstraint("iso_code", name=CURRENCY_ISO_CODE_UNIQUE_CONSTRAINT_NAME),
        CheckConstraint("decimal_places >= 0", name="ck_currencies_decimal_places"),
        CheckConstraint(
            "char_length(iso_code) = 3",
            name="ck_currencies_iso_code_length",
        ),
        CheckConstraint(
            "char_length(iso_numeric) = 3",
            name="ck_currencies_iso_numeric_length",
        ),
    )

    iso_code: Mapped[str] = mapped_column(
        String(length=3),
        nullable=False,
    )
    iso_numeric: Mapped[str] = mapped_column(
        String(length=3),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(length=255),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(
        String(length=16),
        nullable=False,
    )
    decimal_places: Mapped[int] = mapped_column(
        nullable=False,
    )
