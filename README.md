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


## Current V1 Financial Scope

- The target persisted financial model for v1 is `LedgerAccount`, `Tag`, `Transaction`, `Entry` and `EntryTag`.
- The target v1 model does not include `StatementCycle`, `StatementRule`, `Statement`, `Invoice` or `transaction.statement_cycle_id`.
- Credit-card invoices are not persisted as their own aggregate in v1. An invoice is a projection over credit-card `Entry` records.
- Invoice identity is factual on the `Entry`: `statement_closing_date` and `statement_due_date` belong to the entry when the entry represents credit-card liability.
- `effective_at` remains the economic date of the transaction, but it does not define invoice membership by itself.
- The current public financial API surface is intentionally narrow: the currency catalog plus independent `LedgerAccount` and `Tag` flows, and a write-oriented `Transaction` flow.
- `Entry` and `EntryTag` do not have independent CRUD in v1.
- `Transaction` remains the aggregate root of the accounting event, and its public API currently exposes `GET /transaction/list`, `GET /transaction`, `POST`, `PUT`, `POST /transaction/post` and `POST /transaction/void`, always together with balanced subordinate `Entry` writes instead of as an isolated simple CRUD.
- `Transaction` does not own a top-level currency in v1. Each `Entry` references the authoritative `currency_id` for its monetary value.
- `LedgerAccount` does not own a fixed currency column. Read models expose `balances[]` grouped by `currency_id`.


## Engineering Conventions

The codebase prefers explicit, boring names over clever indirection. The main goal is that a reader can identify the architectural role of a type or module from its name alone.

### Naming

- Domain concepts use singular names, for example `User`, `NewUser`, `UserChanges` and `src/core/domain/user.py`.
- CRUD-oriented domain input DTOs should use `Create*Data` for create flows and `Update*Data` for update flows. Use cases should translate `Create*Data` into `New*` and `Update*Data` into `*Changes` before calling output ports.
- Use cases use the `UseCase` suffix and live in `src/core/usecases/`, for example `UserUseCase` and `HealthzUseCase`.
- Core contracts use the `InputPort` and `OutputPort` suffixes and live in `src/core/ports/`.
- Infrastructure concretes include the technology in the name when that matters, for example `SQLAlchemyPostgresUnitOfWork`, `SQLAlchemyUserOutputAdapter` and `ScryptPasswordHasher`.
- Aggregate persistence modules may still use local file names such as `repository.py` even when the exported concrete class uses the `OutputAdapter` suffix. The file name describes the persistence role inside the aggregate module; the class name still carries the architectural role.
- SQLAlchemy table mappings use the `Record` suffix, for example `UserRecord`.
- Mapping files under `models/` are named after the physical table, while aggregate modules stay named after the domain concept. Example: `src/infra/postgres/aggregates/user/models/users.py` contains `UserRecord` for the `users` table.
- Custom domain/application exceptions must use the `Error` suffix. Exceptions should communicate the layer they belong to: domain/application errors stay technology-agnostic, such as `UserNotFoundError` and `UserEmailConflictError`; technical persistence exceptions at the port boundary stay explicit, such as `UserEmailConflictOutputPortError`.
- Enum representation depends on ownership. If a string value is part of an external contract, the boundary-owning layer should define it explicitly instead of leaking another layer's enum serialization.
- Closed vocabularies owned by the core should stay enum-typed across the internal stack instead of degrading into loose strings in ports or persistence mappings. The current `LedgerAccount` decisions follow this rule for `type` and optional `instrument_kind`; ISO currency codes remain constrained validated strings owned by the currency catalog.
- Prefer names that match the scope of the concern. Public endpoint slices may use established transport-oriented names, while narrower technical collaborators should use more precise local names when they describe an implementation detail rather than the public feature.
- Keep behavior names, shared primitive names and transport concern names distinct. Prefer verbs for operations, neutral nouns for reusable core building blocks, and transport-oriented nouns for adapter-specific concerns.
- When naming generic fallback or deterministic secondary behavior, prefer one stable shared prefix instead of mixing near-synonyms across the codebase. In the current codebase, `tie_break_*` is the canonical vocabulary for that kind of concern.
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
- Repositories must not raise domain/application errors directly. They should either return `None` for absence on read-style operations or raise `*OutputPortError` for persistence-bound failures that the use case must translate.
- Aggregates that participate in the same transaction must be exposed explicitly on both the core `UnitOfWorkOutputPort` and the concrete `SQLAlchemyPostgresUnitOfWork`.
- Shared Postgres infrastructure stays at the top of `src/infra/postgres/`; aggregate-specific persistence stays under `src/infra/postgres/aggregates/`.
- `PostgresPersistedRecordMixin` centralizes cross-table persisted fields such as `id`, `created_at`, `updated_at`, `is_deleted` and `deleted_at`.
- Audit timestamps and `deleted_at` are database-owned. The application signals state changes; the database is responsible for writing the authoritative timestamps.
- Soft-deleted rows are invisible to normal reads and updates. Hard delete must be an explicit opt-in behavior when the API or use case requires physical removal.
- Constraint names should be stable and explicit when they carry business meaning, such as the unique email constraint on `users`.
- When the database persists a core-owned closed vocabulary, prefer typed SQLAlchemy enums backed by native Postgres enums instead of unconstrained `VARCHAR` columns. The current `ledger_accounts.type` and optional `ledger_accounts.instrument_kind` columns are the reference pattern for core-owned vocabularies; monetary identity is persisted through `entries.currency_id` references to the currency catalog instead of transaction-level or ledger-account-level currency columns.

### API and Mapping Rules

- HTTP routes should depend on input ports, not concrete use cases.
- API schemas and responses should expose the transport contract, not persistence internals. Password fields, password hashes and internal persistence details must not leak to responses.
- Route handlers should stay thin: validate/parse input, call the input port, translate known domain errors, and map the result to the response schema.
- Small explicit mapper functions such as `_to_user_response(...)` and `_to_domain_user(...)` are preferred over implicit magic conversions.
- The same applies to enums at the boundary: domain enums must not define HTTP response text just because the current adapter serializes them.
- When an enum value is part of the public HTTP contract, the adapter or schema layer owns that textual representation and maps to it explicitly.
- When the domain enum and the boundary enum intentionally share member names, prefer direct enum-to-enum conversion by name, such as `ResponseEnum[domain_value.name]`, instead of maintaining a manual mapping table.
- The same rule applies to non-response contracts. If the adapter exposes a public sort field enum and the core owns a separate internal sort enum, keep the public text in the adapter and derive the core-facing identifier from the internal enum itself rather than from a duplicated string value.
- Operational and protocol enums whose string value is the interface itself may remain `StrEnum`. Current examples include settings/logging enums and sort-related transport identifiers.
- Timestamps exposed by the API must be serialized in UTC using the centralized API schema conventions.
- Shared pagination follows the same split: `src/core/shared/listing.py` owns agnostic list types such as `ListQuery` and `Page[T]`, while the HTTP adapter owns transport-facing types such as `PageResponse[T]`.
- The central HTTP pagination parser lives in the adapter layer and is responsible for translating query params into the core list query type.
- The current central pagination contract supports `offset`, `limit` and optional `sort`; future `filter` and `query` concerns must extend the same shared module instead of introducing route-specific pagination shapes.
- Sort whitelist is configured per endpoint in the HTTP adapter. It must not be a global rule baked into `ListQuery` or shared blindly across unrelated collections.
- Endpoint sort configuration should be explicit and enum-based. The adapter defines the public sortable fields for the endpoint, and maps them to the corresponding core sortable fields when the transport name differs from the domain name.
- The HTTP `sort` contract is a comma-separated string such as `sort=-created_at,+email`. When a term omits the prefix, `+` is assumed.
- The current HTTP defaults are `offset=0`, `limit=settings.fastapi.pagination_default_limit` and `limit<=settings.fastapi.pagination_max_limit`.
- The first concrete paginated collection endpoint is `GET /user/list`. It reuses the shared pagination primitives and returns `PageResponse[UserResponse]`.
- For `GET /user/list`, sortable public fields currently come from `UserResponse`, the default functional order is `created_at ASC`, and the implementation adds a technical `id DESC` tie-break to keep pages stable.
- The user collection endpoint lists only active users; soft-deleted users remain invisible in paginated reads just as they do in normal `GET` flows.
- Paginated HTTP responses should include `items`, `offset`, `limit` and `total`.
- Error-status mapping must reflect the semantic cause, not just the layer where the error was raised. Use `404` for missing resources, `409` for resource-state conflicts such as uniqueness collisions, and `422` when the request is syntactically valid but violates a business rule on existing data.
- The current reference distinction is `UserEmailConflictError -> 409` versus a semantic accounting-rule violation such as providing invoice fields on an entry that does not point to a `LIABILITY` + `CREDIT_CARD` ledger account. A duplicate email is a resource conflict; the latter is valid syntax with invalid business meaning for the requested workflow.

### Security and Hashing Rules

- Password hashing is exposed to the core through `PasswordHasherOutputPort`; the core depends on the intent to hash and verify passwords, not on a concrete algorithm API.
- The concrete implementation lives in infra and may use technology-specific naming, for example `ScryptPasswordHasher`.
- Persisted password hashes must be self-describing. The current canonical format is `scrypt$n=16384$r=8$p=1$dklen=64$salt$hash`.
- Hash parameters such as `n`, `r`, `p` and `dklen` must be explicit in both the implementation and the persisted payload.
- Password verification must recompute the hash from the persisted parameters and compare using a timing-attack-resistant operation.
- The legacy format `scrypt$salt$hash` is not supported.

### Testing Rules

- Unit tests should mirror the source boundary they protect.
- Unit-test folders should follow the same structure as the application folders they cover. For example, tests for `src/core/shared/` should live under `tests/unit/core/shared/`, not directly under `tests/unit/core/`.
- Integration tests should validate real collaboration between components, especially HTTP flows and Postgres persistence behavior.
- Test names should follow the same behavior-oriented pattern across the suite: `test_<action>_<result>_<condition>`. Prefer stable vocabulary such as `returns`, `raises`, `soft_deletes`, `hard_deletes`, `rejects` and `persists` instead of mixing near-synonyms across analogous suites.
- Suites that cover analogous behavior should assert at the same depth. CRUD HTTP tests should validate the relevant response body instead of only status codes, and repository integration tests should validate both the returned result and persisted side effects when persistence is part of the contract being exercised.
- Fixed-response test doubles should use the `Stub` suffix.
- `conftest.py` should own fixture lifecycle and composition only. Shared builders, reusable stateful doubles and focused support helpers belong in a surface-local helper module when they have clear payoff, such as `tests/integration/fastapi/helpers/builders.py`, `tests/integration/fastapi/helpers/stubs.py`, `tests/integration/postgres/helpers/builders.py` and `tests/integration/postgres/helpers/clock.py`.
- Trivial one-line wrappers should stay inline in the suite that uses them. Do not extract helpers that hide less than they remove.
- Redundant tests may be removed only when a remaining test still covers the same real behavior and the coverage run over `src/` stays at `100%`.
- Architectural rules that must remain true across the repository belong in `tests/architecture/`.

### Implementation Guidance

- Prefer the smallest change that fixes the real problem at the owning layer instead of compensating for it from a neighboring layer.
- Prefer explicit code over clever indirection. Small mapper functions, explicit enum conversions and direct wiring are usually better than magic helpers that hide control flow.
- Do not introduce a shared abstraction on first use unless the ownership boundary is already clear and local duplication is actively causing confusion. A second real use case is usually the right moment to extract.
- Keep policy and defaults in the layer that owns the contract. Adapters may choose HTTP defaults and public field names; infra should not silently invent fallback behavior for missing application decisions.
- Keep transport contracts, domain semantics and persistence mechanics separate even when the data looks similar. Similar shape is not enough reason to collapse ownership boundaries.
- Prefer extending an existing shared primitive or helper when the new behavior is genuinely the same concern. Do not create parallel shapes for pagination, filtering, mapping or error handling when the repository already has an established home for that concern.
- When adding generic capabilities, extract only the mechanism that is truly shared. Keep aggregate-specific vocabulary, field maps and business decisions local to the aggregate.
- New names should align with existing canonical vocabulary in the repository. When a concept already has an established prefix or suffix, reuse it instead of introducing a near-synonym.
- Changes that affect public contracts, architectural conventions or cross-cutting rules should update the README in the same cycle.
- Changes should leave behind focused tests for the touched behavior. Prefer the narrowest test that proves the decision, then rely on the broader suite as a safety net.
- Cross-aggregate business invariants belong in the use case that owns the workflow, not in the HTTP route or repository. In the target financial model, the reference rule is the transaction write flow: invoice fields on an `Entry` only make sense when that entry points to a `LedgerAccount` with `type == LIABILITY` and `instrument_kind == CREDIT_CARD`, and that validation should live in the use case that owns the transactional write boundary.

### Financial Modeling Rules

- `LedgerAccount.type` is the primary accounting classification.
- `LedgerAccount.instrument_kind` is an optional operational classification. It is used only when the workflow depends on the represented instrument, such as credit-card invoice semantics.
- `instrument_kind` must remain `None` when no instrument-specific behavior is needed; it does not replace `type`.
- `Transaction` does not own a top-level currency. Each `Entry.currency_id` is the monetary source of truth for that leg of the accounting event.
- `LedgerAccount` does not own a fixed currency field. Account reads expose `balances[]` by `currency_id`.
- A transaction may transition only from `PENDING` to `POSTED` or `VOIDED`.
- `POSTED` is an immutable accounting fact.
- `VOIDED` is terminal and does not return to `PENDING`.
- Correcting a `POSTED` transaction must happen through a new reversal transaction with opposite entries; the system must not support destructive `POSTED -> VOIDED`.


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

Running tests is a standing development premise for this project. Every change must be validated with `make run-tests` to guarantee nothing broke, and with `make run-tests-with-coverage` to guarantee `src/` remains at `100%` coverage.

```bash
make run-tests
```

This runs the suite without coverage for a faster feedback loop and should be the default command during development.

To run coverage over `src/` and fail below `100%`:

```bash
make run-tests-with-coverage
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
make run-tests
make run-tests-with-coverage
```

Development work is only considered complete when all four commands above pass and the coverage run confirms `100%` coverage.


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