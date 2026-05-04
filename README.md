# Finance Manager

The backend system of a financial manager.


## Architecture

The project follows a strict dependency direction:

`Adapter/input -> Port/input -> UseCase -> Domain -> Port/output -> Adapter/output`

- `src/core`: business concepts, rules, contracts and application orchestration.
- `src/adapters`: entry and exit integrations around the core.
- `src/infra`: runtime, assembly, configuration and operational concerns that support the application.

The architectural boundaries are enforced by `pytestarch` tests in `tests/architecture`.


## How To Run Locally

```bash
git clone git@github.com:henry-vg/Finance-Manager.git
cd Finance-Manager/
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r docker/dev/requirements.txt
docker compose -f docker/dev/docker-compose.yml up -d postgres
docker compose -f docker/dev/docker-compose.yml ps postgres  # wait until healthy
CFG_POSTGRES_HOST=localhost alembic upgrade head
CFG_POSTGRES_HOST=postgres uvicorn src.infra.main:create_app --host 0.0.0.0 --factory --reload --reload-dir=src
```


## How To Run With Docker

```bash
docker compose -f docker/dev/docker-compose.yml up --build
```


## How To Test

```bash
pytest -q
```


## How To Run Migrations

```bash
alembic upgrade head
alembic downgrade -1
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

## FEITO

- Renomear use_cases para usecases em todos os lugares da aplicação, inclusive pastas, arquivos e funções/variáveis/classes
- Adicionar created_at e updated_at na tabela user
- Faça um ApiSchemaBase para todos os schemas HTTP, e nela a gente formata os datetimes do jeito que quisermos, de forma centralizada; sempre o formato deve ser no tipo "2026-05-03T17:35:18.123Z"
- Adicionar description e responses nas rotas de users
- Fazer get user by email ao invés de get user by id (sendo assim, o id pode ser incremental no banco, visto que é id interno - ou adotamos a prática de fazer uuid sempre?)

## PENDENTE

- Agora precisamos lidar com ciclo de trabalho transacional do banco de dados (commit/rollback/refresh) da melhor forma, porque no nosso repositor já está duplicando as coisas, como já vimos; faça um plano para resolvermos isso, promovendo para uma abstração explícita de unit of work, definida como port no core e implementada na infra.
---
- Melhor salvar "scrypt$n=16384$r=8$p=1$salt$hash" ao invés de "scrypt$salt$hash" nas senhas; é bom definir dklen explicitamente; Adicionar método de verificação de hashes
---
- Adicionar pagination central
- Adicionar list users
- Atualizar documentação sobre make
---
- Verificar testes e implementações até aqui
- Separar e fazer commits

## DEPOIS

- Adicionar URIs relevantes para 'type' nas respostas que seguem o padrão RFC-9457

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