# Contexto do Projeto

Este é o ponto de entrada curto para agentes e novos mantenedores. Use esta página para orientação rápida e depois avance para a documentação temática em `docs/`.

## Objetivo do sistema

O Finance Manager é uma API backend de gestão financeira pessoal com modelagem contábil de dupla entrada. O núcleo atual cobre usuários, moedas, contas contábeis, tags e transações compostas por múltiplas entries balanceadas.

## Stack

- Python 3.12
- FastAPI + Uvicorn
- Pydantic v2
- SQLAlchemy assíncrono + Postgres + Alembic
- Pytest, pytestarch, Ruff, MyPy e coverage

## Arquitetura

- arquitetura hexagonal com `core`, `adapters` e `infra`;
- composition root em `src/infra/bootstrap.py`;
- app factory HTTP em `src/infra/fastapi/app.py`;
- entrypoint em `src/infra/main.py`;
- boundaries protegidos por `tests/architecture/test_boundaries.py`.

## Módulos principais

- `src/core/domain/`: `User`, `Currency`, `LedgerAccount`, `Tag`, `Transaction`, `Entry`.
- `src/core/usecases/`: orquestração dos fluxos de CRUD, lifecycle e invariantes.
- `src/adapters/input/api/`: rotas, schemas, paginação e tradução de erro HTTP.
- `src/infra/postgres/`: aggregates, repositories, Unit of Work e runtime SQLAlchemy.
- `src/infra/security/`: hash de senha com scrypt.
- `src/infra/exchange_rate/`: adapter cambial atual, hoje mock.

## O que ler por área

- visão geral e snapshot atual: `meta/current-state.md`
- arquitetura e limites: `architecture/hexagonal-architecture.md`
- padrões de código: `architecture/code-patterns-and-preferences.md`
- domínio e decisões de produto: `domain/model-overview.md` e `domain/product-decisions.md`
- transaction, entries e FX: `domain/transactions.md`
- HTTP e contrato público: `api/http-conventions.md`
- Postgres, Unit of Work e migrations: `persistence/postgres-and-migrations.md`
- testes e barra de qualidade: `testing/quality-and-structure.md`
- operação local: `operations/local-development.md`

## Comandos essenciais

```bash
make run-database
make run-migrations
make run-api
make run-quality-check
make run-tests-with-coverage
```

## Ordem de fonte de verdade

1. código e testes atuais
2. `Makefile`, `pyproject.toml` e settings reais
3. `docs/`
4. `README.md`