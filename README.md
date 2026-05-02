# Finance Manager

The backend system of a financial manager.


## Architecture

The project follows a strict dependency direction:

`Adapter/input -> Port/input -> UseCase -> Domain -> Port/output -> Adapter/output`

- `src/core/domain`: pure domain objects and business concepts.
- `src/core/ports`: input and output contracts owned by the core.
- `src/core/use_cases`: application orchestration implementing input ports.
- `src/adapters/input`: driving adapters such as the HTTP API.
- `src/adapters/output`: driven adapters such as databases and external services.
- `src/infra`: composition root, framework wiring, settings and logging.

The architectural boundaries are enforced by `pytestarch` tests in `tests/architecture`.


## How To Run Locally

```bash
git clone git@github.com:henry-vg/Finance-Manager.git
cd Finance-Manager/
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r docker/dev/requirements.txt
uvicorn src.infra.fastapi.app:create_app --factory --reload --reload-dir=src
```


## How To Test

```bash
pytest -q
```


## Quality Checks

```bash
ruff check .
mypy .
pytest -q
```


## Folder Structure

```
Finance-Manager
├── logs                             # Application logs and rotated log files
├── docker                           # Development and production container setup
├── src                              # Main source code of the application
│   ├── adapters                     # Framework-facing adapters
│   │   ├── input                    # Driving adapters
│   │   └── output                   # Driven adapters
│   ├── core                         # Business core
│   │   ├── domain                   # Entities, value objects and domain rules
│   │   ├── ports                    # Core-owned contracts
│   │   └── use_cases                # Use-case orchestration
│   └── infra                        # Composition root and technical infrastructure
└── tests                            # Automated tests
    ├── architecture                 # Architectural boundary enforcement
    ├── integration                  # Integration tests (real components working together)
    └── unit                         # Unit tests (isolated functions/classes)
```


# TODOs

- fazer bootstrap (container) na infra api?
- deixar testes redondos
- o settings não deve ser computado toda vez que é importado
- adicionar URIs relevantes para 'type' nas respostas que seguem o padrão RFC-9457


# Finance Manager Notes

## Notas

- Uma *Transaction* **não tem valor**, ela tem **lançamentos**.
- *Transaction* é **evento**, *Entry* é **fluxo de crédito**.
- Uma *Transaction* tem **2 ou mais *Entries***.
- A soma dos *amount* das *Entries* de uma mesma *Transaction* é **sempre zero**.
- O saldo é a soma dos *Entries* por *LedgerAccount*.
- *Transaction*: **algo aconteceu**; *Entry*: **isso alterou créditos**; *LedgerAccount*: **onde o crédito vive conceitualmente**.
- ***LedgerAccountTypes***:
    - *ASSET - "o que eu tenho"*: créditos que **me pertencem**, por exemplo conta corrente, carteira, poupança, dinheiro a receber, cashback acumulado.
    - *LIABILITY - "o que eu devo"*: créditos que **eu devo a alguém**, por exemplo cartão de crédito, empréstimo, financiamento, cheque especial usado.
    - *INCOME - "de onde vem o dinheiro"*: **fontes de entrada**, por exemplo salário, juros recebidos, cashback recebido (geralmente só aparece em lançamentos e zera no fechamento do período via equity).
    - *EXPENSE - "pra onde vai o dinheiro"*: **consumo**, por exemplo alimentação, aluguel, transporte, lazer.
    - *EQUITY - "patrimônio / ajuste"*: **conta de equilíbrio**, por exemplo saldo inicial, ajustes, fechamento de período, correções manuais (uma conta coringa).
- Tipos contábeis nunca respondem **"o que é isso?"**, sempre respondem **"como isso se comporta?"**.
- Com os *LedgerAccountTypes*, posso impedir *EXPENSE->EXPENSE*, *INCOME->INCOME*, validar se toda a transação tem pelo menos um *ASSET* ou *LIABILITY*, gerar *DRE* automaticamente, fazer balanço patrimonial, fechar períodos contábeis corretamente - tudo sem saber o que é cartão ou banco.

## Modelagem

```python
from datetime import datetime, date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class CurrencyEnum(StrEnum):
    BRL = "BRL"
    USD = "USD"
    EUR = "EUR"


class TransactionStatusEnum(StrEnum):
    PENDING = "PENDING"
    EFFECTIVE = "EFFECTIVE"
    CANCELED = "CANCELED"


class LedgerAccountTypeEnum(StrEnum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    EQUITY = "EQUITY"


class BaseTable:
    id: UUID
    created_at: datetime
    updated_at: datetime


class Category(BaseTable):
    title: str
    parent_category_id: UUID | None


class StatementCycle(BaseTable):
    ledger_account_id: UUID
    due_date: date
    statement_date: date


class LedgerAccount(BaseTable):
    title: str
    type: LedgerAccountTypeEnum


class Transaction(BaseTable):
    effective_at: datetime
    title: str
    description: str
    status: TransactionStatusEnum

class Entry(BaseTable):
    transaction_id: UUID
    ledger_account_id: UUID
    amount: Decimal
    currency: CurrencyEnum
    category_ids: list[UUID]
```