from src.core.domain.currency import (
    CreateCurrencyData,
    Currency,
    CurrencyChanges,
    CurrencyDataValidationError,
    CurrencyISOCodeConflictError,
    CurrencyNotFoundError,
    NewCurrency,
    UpdateCurrencyData,
)
from src.core.ports.input.currency_input_port import CurrencyInputPort
from src.core.ports.output.currency_output_port import (
    CurrencyISOCodeConflictOutputPortError,
    CurrencyNotFoundOutputPortError,
)
from src.core.ports.output.unit_of_work_output_port import UnitOfWorkOutputPortFactory
from src.core.shared import ListQuery, Page


class CurrencyUseCase(CurrencyInputPort):
    def __init__(
        self,
        unit_of_work_output_port_factory: UnitOfWorkOutputPortFactory,
    ) -> None:
        self._unit_of_work_output_port_factory = unit_of_work_output_port_factory

    @staticmethod
    def _normalize_currency_data(
        data: CreateCurrencyData | UpdateCurrencyData,
    ) -> dict[str, str | int]:
        iso_code = data.iso_code.strip().upper()
        iso_numeric = data.iso_numeric.strip()
        name = data.name.strip()
        symbol = data.symbol.strip()

        if not iso_code or not iso_numeric or not name or not symbol:
            raise CurrencyDataValidationError()

        return {
            "iso_code": iso_code,
            "iso_numeric": iso_numeric,
            "name": name,
            "symbol": symbol,
            "decimal_places": data.decimal_places,
        }

    async def list_currencies(
        self,
        list_query: ListQuery,
    ) -> Page[Currency]:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            return await unit_of_work.currencies.list_currencies(list_query=list_query)

    async def get_currency(
        self,
        currency_id: int,
    ) -> Currency:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            currency = await unit_of_work.currencies.get_currency_by_id(
                currency_id=currency_id,
            )

            if currency is None:
                raise CurrencyNotFoundError()

            return currency

    async def create_currency(
        self,
        data: CreateCurrencyData,
    ) -> Currency:
        normalized_data = self._normalize_currency_data(data)

        async with self._unit_of_work_output_port_factory() as unit_of_work:
            try:
                created_currency = await unit_of_work.currencies.create_currency(
                    new_currency=NewCurrency(
                        iso_code=normalized_data["iso_code"],
                        iso_numeric=normalized_data["iso_numeric"],
                        name=normalized_data["name"],
                        symbol=normalized_data["symbol"],
                        decimal_places=normalized_data["decimal_places"],
                    ),
                )
            except CurrencyISOCodeConflictOutputPortError as exc:
                raise CurrencyISOCodeConflictError() from exc

            await unit_of_work.commit()

            return created_currency

    async def update_currency(
        self,
        currency_id: int,
        data: UpdateCurrencyData,
    ) -> Currency:
        normalized_data = self._normalize_currency_data(data)

        async with self._unit_of_work_output_port_factory() as unit_of_work:
            current_currency = await unit_of_work.currencies.get_currency_by_id(
                currency_id=currency_id,
            )

            if current_currency is None:
                raise CurrencyNotFoundError()

            try:
                updated_currency = await unit_of_work.currencies.update_currency(
                    currency_id=currency_id,
                    changes=CurrencyChanges(
                        iso_code=normalized_data["iso_code"],
                        iso_numeric=normalized_data["iso_numeric"],
                        name=normalized_data["name"],
                        symbol=normalized_data["symbol"],
                        decimal_places=normalized_data["decimal_places"],
                    ),
                )
            except CurrencyNotFoundOutputPortError as exc:
                raise CurrencyNotFoundError() from exc
            except CurrencyISOCodeConflictOutputPortError as exc:
                raise CurrencyISOCodeConflictError() from exc

            await unit_of_work.commit()

            return updated_currency

    async def delete_currency(
        self,
        currency_id: int,
        hard_delete: bool = False,
    ) -> None:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            if hard_delete:
                current_currency = (
                    await unit_of_work.currencies.get_currency_by_id_including_deleted(
                        currency_id=currency_id,
                    )
                )
            else:
                current_currency = await unit_of_work.currencies.get_currency_by_id(
                    currency_id=currency_id,
                )

            if current_currency is None:
                raise CurrencyNotFoundError()

            try:
                if hard_delete:
                    await unit_of_work.currencies.hard_delete_currency(
                        currency_id=currency_id,
                    )
                else:
                    await unit_of_work.currencies.soft_delete_currency(
                        currency_id=currency_id,
                    )
            except CurrencyNotFoundOutputPortError as exc:
                raise CurrencyNotFoundError() from exc

            await unit_of_work.commit()
