# Desenvolvimento Local

Esta página concentra o fluxo operacional de desenvolvimento no host local. Para detalhes de domínio, arquitetura ou persistência, use as demais páginas temáticas de `docs/`.

## Pré-requisitos

- Python 3.12
- Docker e Docker Compose
- Git

## Setup inicial

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r docker/dev/requirements.txt
```

## Banco de dados local

```bash
make run-database
make run-migrations
```

Os comandos atuais assumem `CFG_POSTGRES_HOST=localhost` para execução no host.

## Subindo a API

```bash
make run-api
```

O comando atual sobe `src.infra.main:create_app` via Uvicorn com reload em `src/`.

URLs relevantes:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Liveness: `http://localhost:8000/healthz/liveness`
- Readiness: `http://localhost:8000/healthz/readiness`

## Validação local

```bash
make run-tests
make run-tests-with-coverage
make run-quality-check
```

Fluxo recomendado para mudanças normais:

1. rodar o teste mais focado do slice alterado;
2. rodar `make run-quality-check`;
3. rodar `make run-tests-with-coverage` quando a mudança justificar fechamento amplo.

## Arquivos canônicos

- `Makefile`
- `docker/dev/`
- `src/infra/bootstrap.py`
- `src/infra/fastapi/app.py`