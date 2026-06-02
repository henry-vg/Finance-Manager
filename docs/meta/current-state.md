# Estado Atual do MVP

Esta página registra o snapshot técnico e funcional do repositório no estado atual.

## Como usar este arquivo

`current-state.md` representa um snapshot. Atualize-o quando:

- coverage mudar significativamente;
- milestones forem concluídos;
- limitações conhecidas mudarem.

## Estado atual

O MVP atual já entrega uma API backend funcional com arquitetura hexagonal explícita, persistência Postgres assíncrona, migrations via Alembic, documentação OpenAPI, health checks e barra de qualidade alta com cobertura total exigida sobre `src/`.

## Features implementadas

- CRUD e listagem paginada para usuários, moedas, tags e contas contábeis.
- Transações com `create`, `get`, `list`, `update`, `post` e `void`.
- Entries com tags opcionais e datas factuais de fatura para contas `LIABILITY` com `instrument_kind == CREDIT_CARD`.
- Fluxo monetário assimétrico em transaction: escrita com `amount` na moeda de origem, cálculo interno de `amount_in_dollars`, persistência e leitura pública em dólar-base com snapshots cambiais.
- Balanceamento contábil validado em dólar para transactions.
- Soft delete por padrão e hard delete opt-in explícito nos recursos que suportam remoção.
- Hash de senha com scrypt no fluxo de usuários.
- Migrations lineares em `alembic/versions/` com seed determinístico de dados base para desenvolvimento e testes.
- Testes unitários, integração FastAPI, integração Postgres e boundaries arquiteturais.

## Fora do escopo atual

- aggregate separado de fatura de cartão;
- reconciliação bancária;
- importação financeira automatizada;
- integrações de Open Finance;
- IA de classificação ou enriquecimento de transações.

## Débitos conhecidos

- O adapter cambial atual é `src/infra/exchange_rate/mock_exchange_rate_adapter.py`; existe `TODO` explícito para substituí-lo por um provider real de mercado.
- A pasta `docs/adr/` já existe, mas ainda não há ADRs registradas para decisões arquiteturais duráveis.

## Lacunas de teste ou documentação

- Nesta revisão, não foi identificada lacuna crítica de documentação em `.cursor/` ou `docs/`.
- A barra executável de qualidade continua sendo Ruff, MyPy, cobertura total e branch coverage.
- Na validação desta revisão, `make run-tests-with-coverage` executou 405 testes, mas falhou a barra de coverage com `99.62%`; os misses reportados ficaram em `src/core/usecases/transaction_usecase.py` e `src/infra/postgres/aggregates/transaction/repository.py`.

## Próximo marco sugerido

1. Fechar o gap de coverage no slice de transaction.
2. Depois, planejar a substituição do mock de câmbio por provider real, com ADR própria.