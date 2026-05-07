# Finance Manager

The backend system of a financial manager.


## Architecture

The project follows a strict dependency direction:

`Adapter/input -> Port/input -> UseCase -> Domain -> Port/output -> Adapter/output`

- `src/core`: business concepts, rules, contracts and application orchestration.
- `src/adapters`: entry and exit integrations around the core.
- `src/infra`: runtime, assembly, configuration and operational concerns that support the application.

Transactional work is coordinated explicitly through a Unit of Work:

- use cases depend on a core-owned `UnitOfWorkOutputPortFactory` port.
- the Postgres implementation opens one async session per use-case execution.
- the infrastructure exposes the Postgres Unit of Work factory through the composition root; the concrete Unit of Work is not part of the public wiring surface.
- repositories are session-bound and may `flush`/`refresh`, but they do not `commit` or `rollback`.
- aggregates that participate in the same transactional boundary must be added explicitly to both `UnitOfWorkOutputPort` and `SQLAlchemyPostgresUnitOfWork`.

Postgres persistence follows an aggregate-oriented organization:

- `src/infra/postgres/aggregates/<aggregate>/` names the aggregate persistence module, not a physical table.
- aggregate modules stay singular when they represent a singular domain concept, for example `src/infra/postgres/aggregates/user/`.
- SQLAlchemy mappings for physical tables live under `src/infra/postgres/aggregates/<aggregate>/models/`.
- model files are named after the physical table, for example `src/infra/postgres/aggregates/user/models/users.py` for the `users` table.
- one repository may depend on multiple table models; repository boundaries do not need to match table boundaries.
- shared Postgres-only plumbing, such as integrity-error inspection, belongs in `src/infra/postgres/` and not inside a single aggregate module.

Postgres audit and deletion semantics are database-owned:

- `PostgresPersistedRecordMixin` centralizes `id`, `created_at`, `updated_at`, `is_deleted` and `deleted_at` for persisted records.
- `updated_at` and `deleted_at` are set by database trigger logic, not by application timestamps.
- the default `DELETE /user` behavior is a soft delete; `hard_delete=true` is required for physical row removal.
- soft-deleted users are invisible to normal `GET`, `UPDATE` and default `DELETE` flows.
- soft delete does not release the unique `email`; a soft-deleted user still blocks email reuse.

When adding a new aggregate that must participate in the same transactional boundary:

- add its output-port property to the core `UnitOfWorkOutputPort` contract.
- wire its concrete repository inside `SQLAlchemyPostgresUnitOfWork`.
- expose it through the active unit of work instead of opening a separate session in the use case.

The architectural boundaries are enforced by `pytestarch` tests in `tests/architecture`.


## Engineering Conventions

The codebase prefers explicit, boring names over clever indirection. The main goal is that a reader can identify the architectural role of a type or module from its name alone.

### Naming

- Domain concepts use singular names, for example `User`, `NewUser`, `UserChanges` and `src/core/domain/user.py`.
- Use cases use the `UseCase` suffix and live in `src/core/usecases/`, for example `UserUseCase` and `HealthzUseCase`.
- Core contracts use the `InputPort` and `OutputPort` suffixes and live in `src/core/ports/`.
- Infrastructure concretes include the technology in the name when that matters, for example `SQLAlchemyPostgresUnitOfWork`, `SQLAlchemyUserOutputAdapter` and `ScryptPasswordHasher`.
- SQLAlchemy table mappings use the `Record` suffix, for example `UserRecord`.
- Mapping files under `models/` are named after the physical table, while aggregate modules stay named after the domain concept. Example: `src/infra/postgres/aggregates/user/models/users.py` contains `UserRecord` for the `users` table.
- Exceptions should communicate the layer they belong to. Domain/application errors stay technology-agnostic, such as `UserNotFoundError` and `UserEmailConflictError`; technical persistence exceptions at the port boundary stay explicit, such as `UserEmailConflictOutputPortError`.
- Prefer f-strings over `.format()` for string interpolation.
- Prefer `dataclass` for simple internal data carriers with little or no validation behavior.
- Prefer inheriting from Pydantic `BaseModel` whenever a structure needs more robust validation, parsing or serialization behavior, even when the type is reused outside HTTP boundaries.

### Layer Responsibilities

- `src/core/domain/` contains technology-agnostic business structures and domain errors. It must not know FastAPI, SQLAlchemy, Postgres, Scrypt or any other framework detail.
- `src/core/ports/` defines the contracts the core depends on. Ports are owned by the core, even when infra implements them.
- `src/core/usecases/` orchestrates business flows. A use case coordinates ports, enforces application rules, translates technical output-port errors into domain/application errors and decides transactional boundaries through the Unit of Work port.
- `src/core/shared/` contains technology-agnostic primitives reused across multiple core slices but that do not belong to a specific domain concept, port contract or single use case.
- `src/core/shared/` is the right place for cross-cutting application-level types such as pagination/listing primitives that must be reused by ports, use cases and adapters without becoming HTTP-specific or persistence-specific.
- `src/core/shared/` should not become a generic dump for unrelated helpers. It should be used only for small, stable, cross-cutting building blocks with clear semantics and no framework dependency.
- `src/adapters/input/` translates framework inputs into core calls and translates core outputs/errors into transport-specific responses. In HTTP routes, this means building request DTOs, calling an input port and mapping domain errors to `HTTPException`.
- `src/adapters/output/` is reserved for driven adapters that sit around the core contract when a dedicated adapter layer is useful.
- `src/infra/` owns concrete technologies, runtime wiring and operational concerns. FastAPI app assembly, Postgres sessions, SQLAlchemy repositories, logging and security implementations belong here.
- `src/infra/bootstrap.py` is the composition root. It wires concrete infra implementations into core use cases and exposes only the assembled application dependencies.
- Application configuration belongs in `src/infra/settings/`. Defaults, operational limits and environment-driven toggles should be centralized there instead of being duplicated as hardcoded constants across adapters, use cases or infrastructure modules.

### Transaction and Persistence Rules

- The core does not open database sessions directly. It asks for a `UnitOfWorkOutputPortFactory` and works through the repositories exposed by the active unit of work.
- The concrete Unit of Work lives in infra and is technology-specific. The core sees only the port.
- Repositories are session-bound. They may `flush()` and `refresh()` entities, but they do not `commit()` or `rollback()` transactions.
- Aggregates that participate in the same transaction must be exposed explicitly on both the core `UnitOfWorkOutputPort` and the concrete `SQLAlchemyPostgresUnitOfWork`.
- Shared Postgres infrastructure stays at the top of `src/infra/postgres/`; aggregate-specific persistence stays under `src/infra/postgres/aggregates/`.
- `PostgresPersistedRecordMixin` centralizes cross-table persisted fields such as `id`, `created_at`, `updated_at`, `is_deleted` and `deleted_at`.
- Audit timestamps and `deleted_at` are database-owned. The application signals state changes; the database is responsible for writing the authoritative timestamps.
- Soft-deleted rows are invisible to normal reads and updates. Hard delete must be an explicit opt-in behavior when the API or use case requires physical removal.
- Constraint names should be stable and explicit when they carry business meaning, such as the unique email constraint on `users`.

### API and Mapping Rules

- HTTP routes should depend on input ports, not concrete use cases.
- API schemas and responses should expose the transport contract, not persistence internals. Password fields, password hashes and internal persistence details must not leak to responses.
- Route handlers should stay thin: validate/parse input, call the input port, translate known domain errors, and map the result to the response schema.
- Small explicit mapper functions such as `_to_user_response(...)` and `_to_domain_user(...)` are preferred over implicit magic conversions.
- Timestamps exposed by the API must be serialized in UTC using the centralized API schema conventions.
- Shared pagination follows the same split: `src/core/shared/listing.py` owns agnostic list types such as `ListQuery` and `Page[T]`, while the HTTP adapter owns transport-facing types such as `PageResponse[T]`.
- The central HTTP pagination parser lives in the adapter layer and is responsible for translating query params into the core list query type.
- The current central pagination contract supports only `offset` and `limit`; future `sort`, `filter` and `query` concerns must extend the same shared module instead of introducing route-specific pagination shapes.
- The current HTTP defaults are `offset=0`, `limit=settings.fastapi.pagination_default_limit` and `limit<=settings.fastapi.pagination_max_limit`.
- The first concrete paginated collection endpoint is `GET /user/list`. It reuses the shared pagination primitives and returns `PageResponse[UserResponse]`.
- The user collection endpoint lists only active users; soft-deleted users remain invisible in paginated reads just as they do in normal `GET` flows.
- Paginated HTTP responses should include `items`, `offset`, `limit` and `total`.

### Security and Hashing Rules

- Password hashing is exposed to the core through `PasswordHasherOutputPort`; the core depends on the intent to hash and verify passwords, not on a concrete algorithm API.
- The concrete implementation lives in infra and may use technology-specific naming, for example `ScryptPasswordHasher`.
- Persisted password hashes must be self-describing. The current canonical format is `scrypt$n=16384$r=8$p=1$dklen=64$salt$hash`.
- Hash parameters such as `n`, `r`, `p` and `dklen` must be explicit in both the implementation and the persisted payload.
- Password verification must recompute the hash from the persisted parameters and compare using a timing-attack-resistant operation.
- The legacy format `scrypt$salt$hash` is not supported.

### Testing Rules

- Unit tests should mirror the source boundary they protect.
- Integration tests should validate real collaboration between components, especially HTTP flows and Postgres persistence behavior.
- Fixed-response test doubles should use the `Stub` suffix.
- Architectural rules that must remain true across the repository belong in `tests/architecture/`.


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
│   │   ├── shared                   # Stable, technology-agnostic primitives reused across core boundaries
│   │   └── usecases                 # Use-case orchestration
│   └── infra                        # Composition root and technical infrastructure
│       └── postgres                 # Postgres runtime, shared helpers and aggregate persistence modules
│           ├── integrity.py         # Shared Postgres integrity-error inspection helpers
│           ├── unit_of_work.py      # Transaction boundary wiring for aggregate repositories
│           └── aggregates
│               └── user             # Aggregate-oriented persistence module for User
│                   ├── repository.py # SQLAlchemy implementation of the user output port
│                   └── models
│                       └── users.py # SQLAlchemy mapping for the physical users table
└── tests                            # Automated tests
    ├── architecture                 # Architectural boundary enforcement
    ├── integration                  # Integration tests (real components working together)
    └── unit                         # Unit tests (isolated functions/classes)
```


# TODOs

## AGORA

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