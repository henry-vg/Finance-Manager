# Postgres, Unit of Work e Migrations

O projeto usa SQLAlchemy assíncrono com Postgres e Alembic, mas a organização da persistência continua subordinada ao desenho do domínio e das fronteiras transacionais.

## Organização por aggregate

O padrão em `src/infra/postgres/aggregates/` é:

- uma pasta por aggregate;
- modelos físicos em `models/`;
- arquivos de modelo com o nome da tabela física;
- repositório do aggregate em `repository.py`.

Exemplo:

- `src/infra/postgres/aggregates/user/models/users.py`
- `src/infra/postgres/aggregates/user/repository.py`

## Unit of Work

O core não abre sessão diretamente. Ele trabalha por `UnitOfWorkOutputPortFactory`, e a implementação concreta da unidade de trabalho vive na infra.

Consequências práticas:

- a fronteira transacional pertence ao use case;
- repositórios são session-bound;
- repositórios podem usar `flush()` e `refresh()`, mas não fazem `commit()` nem `rollback()`;
- se um aggregate participa da mesma transação, ele precisa aparecer no contrato do Unit of Work e na implementação concreta.

## Campos persistidos compartilhados

`PostgresPersistedRecordMixin` centraliza:

- `id`
- `created_at`
- `updated_at`
- `is_deleted`
- `deleted_at`

Regras importantes:

- `updated_at` e `deleted_at` são database-owned;
- soft delete é o padrão;
- hard delete é opt-in explícito.

## Shape atual de `entries`

Na persistência de transaction, `EntryRecord` grava hoje:

- `transaction_id`
- `ledger_account_id`
- `currency_id`
- `amount_in_dollars`
- `planned_exchange_rate_to_dollars`
- `posting_exchange_rate_to_dollars`
- `statement_closing_date`
- `statement_due_date`

O `amount` original não é reconstruído nem persistido no repositório.

## Migrations

As migrations vivem em `alembic/versions/` e devem manter uma cadeia monótona simples.

Ao editar migrations:

- use nomes claros e ordenados;
- evite forks desnecessários na história do Alembic;
- valide `alembic upgrade head`;
- mantenha backfills e seeds determinísticos;
- não dependa de código de runtime ou chamadas externas para popular dados históricos.

## Arquivos canônicos

- `src/infra/postgres/unit_of_work.py`
- `src/infra/postgres/aggregates/`
- `src/infra/postgres/base.py`
- `alembic/versions/`