from src.core.domain.ledger_account import (
    CreateLedgerAccountData,
    LedgerAccount,
    LedgerAccountChanges,
    LedgerAccountCurrencyISOCodeNotSupportedError,
    LedgerAccountNotFoundError,
    NewLedgerAccount,
    UpdateLedgerAccountData,
)
from src.core.ports.input.ledger_account_input_port import LedgerAccountInputPort
from src.core.ports.output.ledger_account_output_port import (
    LedgerAccountNotFoundOutputPortError,
)
from src.core.ports.output.unit_of_work_output_port import UnitOfWorkOutputPortFactory
from src.core.shared import ListQuery, Page


class LedgerAccountUseCase(LedgerAccountInputPort):
    def __init__(
        self,
        unit_of_work_output_port_factory: UnitOfWorkOutputPortFactory,
    ) -> None:
        self._unit_of_work_output_port_factory = unit_of_work_output_port_factory

    @staticmethod
    def _normalize_currency_iso_code(
        currency_iso_code: str,
    ) -> str:
        return currency_iso_code.strip().upper()

    async def list_ledger_accounts(
        self,
        list_query: ListQuery,
    ) -> Page[LedgerAccount]:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            return await unit_of_work.ledger_accounts.list_ledger_accounts(
                list_query=list_query,
            )

    async def get_ledger_account(
        self,
        ledger_account_id: int,
    ) -> LedgerAccount:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            ledger_account = (
                await unit_of_work.ledger_accounts.get_ledger_account_by_id(
                    ledger_account_id=ledger_account_id,
                )
            )

            if ledger_account is None:
                raise LedgerAccountNotFoundError()

            return ledger_account

    async def create_ledger_account(
        self,
        data: CreateLedgerAccountData,
    ) -> LedgerAccount:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            normalized_currency_iso_code = self._normalize_currency_iso_code(
                data.currency_iso_code,
            )
            currency = await unit_of_work.currencies.get_currency_by_iso_code(
                iso_code=normalized_currency_iso_code,
            )

            if currency is None:
                raise LedgerAccountCurrencyISOCodeNotSupportedError()

            created_ledger_account = (
                await unit_of_work.ledger_accounts.create_ledger_account(
                    new_ledger_account=NewLedgerAccount(
                        title=data.title,
                        type=data.type,
                        kind=data.kind,
                        currency_iso_code=normalized_currency_iso_code,
                    ),
                )
            )

            await unit_of_work.commit()

            return created_ledger_account

    async def update_ledger_account(
        self,
        ledger_account_id: int,
        data: UpdateLedgerAccountData,
    ) -> LedgerAccount:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            current_ledger_account = (
                await unit_of_work.ledger_accounts.get_ledger_account_by_id(
                    ledger_account_id=ledger_account_id,
                )
            )

            if current_ledger_account is None:
                raise LedgerAccountNotFoundError()

            normalized_currency_iso_code = self._normalize_currency_iso_code(
                data.currency_iso_code,
            )
            currency = await unit_of_work.currencies.get_currency_by_iso_code(
                iso_code=normalized_currency_iso_code,
            )

            if currency is None:
                raise LedgerAccountCurrencyISOCodeNotSupportedError()

            try:
                updated_ledger_account = (
                    await unit_of_work.ledger_accounts.update_ledger_account(
                        ledger_account_id=ledger_account_id,
                        changes=LedgerAccountChanges(
                            title=data.title,
                            type=data.type,
                            kind=data.kind,
                            currency_iso_code=normalized_currency_iso_code,
                        ),
                    )
                )
            except LedgerAccountNotFoundOutputPortError as exc:
                raise LedgerAccountNotFoundError() from exc

            await unit_of_work.commit()

            return updated_ledger_account

    async def delete_ledger_account(
        self,
        ledger_account_id: int,
        hard_delete: bool = False,
    ) -> None:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            ledger_accounts = unit_of_work.ledger_accounts

            if hard_delete:
                current_ledger_account = (
                    await ledger_accounts.get_ledger_account_by_id_including_deleted(
                        ledger_account_id=ledger_account_id,
                    )
                )
            else:
                current_ledger_account = await ledger_accounts.get_ledger_account_by_id(
                    ledger_account_id=ledger_account_id,
                )

            if current_ledger_account is None:
                raise LedgerAccountNotFoundError()

            if hard_delete:
                try:
                    await ledger_accounts.hard_delete_ledger_account(
                        ledger_account_id=ledger_account_id,
                    )
                except LedgerAccountNotFoundOutputPortError as exc:
                    raise LedgerAccountNotFoundError() from exc
            else:
                try:
                    await ledger_accounts.soft_delete_ledger_account(
                        ledger_account_id=ledger_account_id,
                    )
                except LedgerAccountNotFoundOutputPortError as exc:
                    raise LedgerAccountNotFoundError() from exc

            await unit_of_work.commit()
