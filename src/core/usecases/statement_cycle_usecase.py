from src.core.domain.ledger_account import (
    LedgerAccountKind,
    LedgerAccountNotFoundError,
    LedgerAccountType,
)
from src.core.domain.statement_cycle import (
    CreateStatementCycleData,
    NewStatementCycle,
    StatementCycle,
    StatementCycleChanges,
    StatementCycleLedgerAccountInvalidError,
    StatementCycleNotFoundError,
    UpdateStatementCycleData,
)
from src.core.ports.input.statement_cycle_input_port import StatementCycleInputPort
from src.core.ports.output.statement_cycle_output_port import (
    StatementCycleNotFoundOutputPortError,
)
from src.core.ports.output.unit_of_work_output_port import (
    UnitOfWorkOutputPort,
    UnitOfWorkOutputPortFactory,
)
from src.core.shared import ListQuery, Page


class StatementCycleUseCase(StatementCycleInputPort):
    def __init__(
        self,
        unit_of_work_output_port_factory: UnitOfWorkOutputPortFactory,
    ) -> None:
        self._unit_of_work_output_port_factory = unit_of_work_output_port_factory

    async def list_statement_cycles(
        self,
        list_query: ListQuery,
    ) -> Page[StatementCycle]:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            return await unit_of_work.statement_cycles.list_statement_cycles(
                list_query=list_query,
            )

    async def get_statement_cycle(
        self,
        statement_cycle_id: int,
    ) -> StatementCycle:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            statement_cycle = (
                await unit_of_work.statement_cycles.get_statement_cycle_by_id(
                    statement_cycle_id=statement_cycle_id,
                )
            )

            if statement_cycle is None:
                raise StatementCycleNotFoundError()

            return statement_cycle

    async def create_statement_cycle(
        self,
        data: CreateStatementCycleData,
    ) -> StatementCycle:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            await self._require_credit_card_ledger_account(
                unit_of_work_output_port=unit_of_work,
                ledger_account_id=data.ledger_account_id,
            )

            created_statement_cycle = (
                await unit_of_work.statement_cycles.create_statement_cycle(
                    new_statement_cycle=NewStatementCycle(
                        ledger_account_id=data.ledger_account_id,
                        cycle_start=data.cycle_start,
                        cycle_end=data.cycle_end,
                        closing_date=data.closing_date,
                        due_date=data.due_date,
                    ),
                )
            )

            await unit_of_work.commit()

            return created_statement_cycle

    async def update_statement_cycle(
        self,
        statement_cycle_id: int,
        data: UpdateStatementCycleData,
    ) -> StatementCycle:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            current_statement_cycle = (
                await unit_of_work.statement_cycles.get_statement_cycle_by_id(
                    statement_cycle_id=statement_cycle_id,
                )
            )

            if current_statement_cycle is None:
                raise StatementCycleNotFoundError()

            await self._require_credit_card_ledger_account(
                unit_of_work_output_port=unit_of_work,
                ledger_account_id=data.ledger_account_id,
            )

            try:
                updated_statement_cycle = (
                    await unit_of_work.statement_cycles.update_statement_cycle(
                        statement_cycle_id=statement_cycle_id,
                        changes=StatementCycleChanges(
                            ledger_account_id=data.ledger_account_id,
                            cycle_start=data.cycle_start,
                            cycle_end=data.cycle_end,
                            closing_date=data.closing_date,
                            due_date=data.due_date,
                        ),
                    )
                )
            except StatementCycleNotFoundOutputPortError as exc:
                raise StatementCycleNotFoundError() from exc

            await unit_of_work.commit()

            return updated_statement_cycle

    async def delete_statement_cycle(
        self,
        statement_cycle_id: int,
        hard_delete: bool = False,
    ) -> None:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            statement_cycles = unit_of_work.statement_cycles

            if hard_delete:
                current_statement_cycle = (
                    await statement_cycles.get_statement_cycle_by_id_including_deleted(
                        statement_cycle_id=statement_cycle_id,
                    )
                )
            else:
                current_statement_cycle = (
                    await statement_cycles.get_statement_cycle_by_id(
                        statement_cycle_id=statement_cycle_id,
                    )
                )

            if current_statement_cycle is None:
                raise StatementCycleNotFoundError()

            if hard_delete:
                try:
                    await statement_cycles.hard_delete_statement_cycle(
                        statement_cycle_id=statement_cycle_id,
                    )
                except StatementCycleNotFoundOutputPortError as exc:
                    raise StatementCycleNotFoundError() from exc
            else:
                try:
                    await statement_cycles.soft_delete_statement_cycle(
                        statement_cycle_id=statement_cycle_id,
                    )
                except StatementCycleNotFoundOutputPortError as exc:
                    raise StatementCycleNotFoundError() from exc

            await unit_of_work.commit()

    async def _require_credit_card_ledger_account(
        self,
        *,
        unit_of_work_output_port: UnitOfWorkOutputPort,
        ledger_account_id: int,
    ) -> None:
        ledger_account = (
            await unit_of_work_output_port.ledger_accounts.get_ledger_account_by_id(
                ledger_account_id=ledger_account_id,
            )
        )

        if ledger_account is None:
            raise LedgerAccountNotFoundError()

        if (
            ledger_account.type != LedgerAccountType.LIABILITY
            or ledger_account.kind != LedgerAccountKind.CREDIT_CARD
        ):
            raise StatementCycleLedgerAccountInvalidError()
