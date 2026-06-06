# Finance Manager

Finance Manager é a API backend de um sistema de gestão financeira pessoal construída com modelagem contábil de dupla entrada. O projeto organiza usuários, contas contábeis, moedas, tags e transações compostas por múltiplos lançamentos balanceados, com foco em consistência de domínio, rastreabilidade e previsibilidade operacional.

Na versão 1.0.0, o sistema cobre o núcleo do fluxo financeiro: cadastro de usuários, catálogo de moedas, contas como banco, carteira e cartão de crédito, classificação por tags, escrita e consulta de transações com múltiplas entries, transição explícita de status contábil e documentação OpenAPI pronta para uso.

## Conceitos centrais

### Ledger Account

Uma `LedgerAccount` representa um recipiente contábil onde os créditos vivem conceitualmente. O tipo contábil da conta define como ela participa do ledger, enquanto `instrument_kind` identifica comportamentos operacionais específicos, como conta bancária, carteira ou cartão de crédito.

### Transaction

Uma `Transaction` representa um evento contábil. Ela não carrega um valor próprio: carrega identidade, data efetiva, descrição, status e um conjunto de `Entries` subordinadas.

### Entry

Uma `Entry` é o efeito de uma transação sobre um saldo. No contrato de escrita, cada entry recebe `ledger_account_id`, `currency_id` e `amount` assinado na moeda de origem. A aplicação resolve `amount_in_dollars` internamente para balanceamento contábil e persistência. Em uma mesma transação, o balanceamento contábil atual precisa zerar em dólar.

### Tag

`Tag` é uma classificação flexível para organização, busca e agrupamento. Ela não é a fonte de verdade para regras contábeis ou cálculo de saldo.

### Currency

O sistema suporta catálogo de moedas e toda referência para moeda acontece por ID. A identidade monetária da operação fica em cada `Entry`, e não na transação como um todo.

## Arquitetura

O projeto segue arquitetura hexagonal para manter regras de negócio isoladas de framework HTTP, banco de dados e detalhes de infraestrutura.

```text
Adapter/Input -> Port/Input -> UseCase -> Domain -> Port/Output -> Adapter/Output
```

Em alto nível:

- `src/core` concentra domínio, casos de uso, contratos e primitivas compartilhadas
- `src/adapters` traduz entradas e saídas entre o core e o mundo externo
- `src/infra` monta a aplicação, configura runtime e implementa detalhes tecnológicos

Essa separação permite evoluir regras de negócio com baixo acoplamento, manter a API previsível e proteger limites arquiteturais com testes automatizados.

## Estrutura de pastas

```text
Finance-Manager/
|-- alembic/               # migrações de banco de dados
|-- docs/                  # documentação técnica interna e de longa duração
|-- docker/                # setup de containers de desenvolvimento e produção
|-- logs/                  # arquivos de log da aplicação
|-- src/
|   |-- adapters/          # adaptadores de entrada e saída
|   |-- core/              # domínio, use cases, ports e shared
|   `-- infra/             # bootstrap, FastAPI, Postgres, segurança e settings
|-- tests/
|   |-- architecture/      # proteção de limites arquiteturais
|   |-- integration/       # testes com colaboração real entre componentes
|   `-- unit/              # testes isolados por módulo
|-- Makefile               # comandos principais de execução e validação
|-- README.md              # apresentação pública do projeto
```

## Como rodar localmente

### Pré-requisitos

- Python 3.12
- Docker e Docker Compose
- Git

### 1. Clonar o repositório

```bash
git clone git@github.com:henry-vg/Finance-Manager.git
cd Finance-Manager
```

### 2. Criar ambiente virtual e instalar dependências

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r docker/dev/requirements.txt
```

### 3. Subir o banco de dados

```bash
make run-database
```

### 4. Aplicar migrações

```bash
make run-migrations
```

### 5. Iniciar a API

```bash
make run-api
```

Com a aplicação em execução:

- Swagger UI: `http://localhost:8000/docs`
- Liveness: `http://localhost:8000/healthz/liveness`
- Readiness: `http://localhost:8000/healthz/readiness`

## Como rodar testes

Para rodar a suíte sem cobertura:

```bash
make run-tests
```

Para rodar a suíte com cobertura completa:

```bash
make run-tests-with-coverage
```

## Como rodar quality checks

Para lint e type checking:

```bash
make run-quality-check
```