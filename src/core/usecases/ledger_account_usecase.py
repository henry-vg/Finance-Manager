from src.core.domain.ledger_account import (
    CreateLedgerAccountData,
    LedgerAccount,
    LedgerAccountChanges,
    LedgerAccountInstrumentKindNotAllowedError,
    LedgerAccountNotFoundError,
    NewLedgerAccount,
    UpdateLedgerAccountData,
    can_assign_ledger_account_instrument_kind,
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
    def _ensure_instrument_kind_allowed(
        data: CreateLedgerAccountData | UpdateLedgerAccountData,
    ) -> None:
        if not can_assign_ledger_account_instrument_kind(
            ledger_account_type=data.type,
            instrument_kind=data.instrument_kind,
        ):
            raise LedgerAccountInstrumentKindNotAllowedError()

    @staticmethod
    def _to_new_ledger_account(
        data: CreateLedgerAccountData,
    ) -> NewLedgerAccount:
        return NewLedgerAccount(
            title=data.title,
            type=data.type,
            instrument_kind=data.instrument_kind,
        )

    @staticmethod
    def _to_ledger_account_changes(
        data: UpdateLedgerAccountData,
    ) -> LedgerAccountChanges:
        return LedgerAccountChanges(
            title=data.title,
            type=data.type,
            instrument_kind=data.instrument_kind,
        )

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
        self._ensure_instrument_kind_allowed(data)
        new_ledger_account = self._to_new_ledger_account(data)

        async with self._unit_of_work_output_port_factory() as unit_of_work:
            created_ledger_account = (
                await unit_of_work.ledger_accounts.create_ledger_account(
                    new_ledger_account=new_ledger_account,
                )
            )

            await unit_of_work.commit()

            return created_ledger_account

    async def update_ledger_account(
        self,
        ledger_account_id: int,
        data: UpdateLedgerAccountData,
    ) -> LedgerAccount:
        self._ensure_instrument_kind_allowed(data)
        changes = self._to_ledger_account_changes(data)

        async with self._unit_of_work_output_port_factory() as unit_of_work:
            current_ledger_account = (
                await unit_of_work.ledger_accounts.get_ledger_account_by_id(
                    ledger_account_id=ledger_account_id,
                )
            )

            if current_ledger_account is None:
                raise LedgerAccountNotFoundError()

            try:
                updated_ledger_account = (
                    await unit_of_work.ledger_accounts.update_ledger_account(
                        ledger_account_id=ledger_account_id,
                        changes=changes,
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
            get_ledger_account = (
                ledger_accounts.get_ledger_account_by_id_including_deleted
                if hard_delete
                else ledger_accounts.get_ledger_account_by_id
            )
            current_ledger_account = await get_ledger_account(
                ledger_account_id=ledger_account_id,
            )

            if current_ledger_account is None:
                raise LedgerAccountNotFoundError()

            try:
                if hard_delete:
                    await ledger_accounts.hard_delete_ledger_account(
                        ledger_account_id=ledger_account_id,
                    )
                else:
                    await ledger_accounts.soft_delete_ledger_account(
                        ledger_account_id=ledger_account_id,
                    )
            except LedgerAccountNotFoundOutputPortError as exc:
                raise LedgerAccountNotFoundError() from exc

            await unit_of_work.commit()
