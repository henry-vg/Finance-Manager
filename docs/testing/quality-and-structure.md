# Testes e Barra de Qualidade

A qualidade do repositório é explicitamente alta e executável. O Cursor deve assumir isso como restrição de trabalho, não como aspiração opcional.

## Estrutura da suíte

- `tests/unit/`: testes isolados por módulo.
- `tests/integration/fastapi/`: colaboração real na superfície HTTP.
- `tests/integration/postgres/`: persistência e infraestrutura real.
- `tests/architecture/`: proteção dos limites arquiteturais.

As suítes devem espelhar a estrutura da aplicação quando a fronteira fizer sentido.

## Convenções importantes

- Prefira nomes comportamentais como `test_<acao>_<resultado>_<condicao>`.
- Use `Stub` para doubles fixos.
- `conftest.py` deve cuidar de composição e ciclo de fixtures, não virar depósito de builders.
- Suites CRUD e rotas devem reutilizar os helpers compartilhados já existentes em vez de recriar payloads e doubles sem necessidade.

## Helpers compartilhados

- FastAPI: `tests/integration/fastapi/helpers/builders.py`
- FastAPI stubs: `tests/integration/fastapi/helpers/stubs.py`
- Postgres: `tests/integration/postgres/helpers/`

## Barra de qualidade atual

- cobertura exigida: `100%` sobre `src/`
- branch coverage obrigatória
- lint com Ruff
- type checking com MyPy

Comandos canônicos:

```bash
make run-tests
make run-tests-with-coverage
make run-quality-check
```

## Estratégia de validação

- rode primeiro a validação mais focada possível para o slice alterado;
- se a mudança ampliar superfície ou assinatura compartilhada, amplie a validação;
- não reduza cobertura para “passar”; ajuste testes e documentação junto.

## Arquivos canônicos

- `pyproject.toml`
- `Makefile`
- `tests/architecture/test_boundaries.py`