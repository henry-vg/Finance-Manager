# instructions.md

Este arquivo existe para dar contexto técnico profundo a qualquer IA ou contribuidor que precise trabalhar no repositório com entendimento real do domínio, da arquitetura, das convenções e dos limites do projeto.

## Papel de cada documento

- `README.md`: documento público do projeto, voltado a apresentar o sistema, explicar o que ele faz e mostrar como rodar e validar a aplicação
- `instructions.md`: documento técnico aprofundado, voltado a desenvolvimento, manutenção e automação assistida por IA
- `notes.md`: anotações pessoais do mantenedor para decisão de alto nível e backlog; não é documento canônico de produto nem guia de implementação obrigatório

Ao trabalhar no repositório, trate `README.md` como a vitrine pública do projeto e `instructions.md` como a fonte de contexto técnico detalhado. Use `notes.md` apenas como apoio de contexto, nunca como contrato definitivo sem confirmar no código.

## Resumo do produto

Finance Manager é uma API backend de gestão financeira pessoal baseada em contabilidade de dupla entrada. O sistema trabalha com usuários, moedas, contas contábeis, tags e transações. A unidade contábil fundamental é a `Entry`: cada transação é composta por duas ou mais entries, e a soma dos valores de todas as entries da mesma transação precisa ser zero.

O foco da v1.0.0 é entregar o núcleo contábil e operacional do produto:

- CRUD de usuários
- CRUD de moedas
- CRUD de contas contábeis
- CRUD de tags
- escrita, leitura, listagem, atualização e transição de status de transações
- health checks e documentação OpenAPI

## Superfície funcional atual

### Endpoints públicos

- `GET /docs`
- `GET /openapi.json`
- `GET /healthz/liveness`
- `GET /healthz/readiness`
- `GET|POST|PUT|DELETE /currency`
- `GET /currency/list`
- `GET|POST|PUT|DELETE /ledger-account`
- `GET /ledger-account/list`
- `GET|POST|PUT|DELETE /tag`
- `GET /tag/list`
- `GET|POST|PUT|DELETE /user`
- `GET /user/list`
- `GET|POST|PUT /transaction`
- `GET /transaction/list`
- `POST /transaction/post`
- `POST /transaction/void`

### Metadados públicos do app

Os metadados do runtime são carregados via `src/infra/settings/models.py` e, no ambiente de desenvolvimento, os defaults de `docker/dev/.env` definem:

- título: `Finance Manager API`
- descrição: `The API system of a financial manager.`
- versão: `1.0.0`
- docs: `/docs`
- openapi: `/openapi.json`

## Modelo de domínio

### Princípio contábil central

- `Transaction` representa o evento contábil
- `Entry` representa o efeito desse evento sobre um saldo
- uma `Transaction` tem duas ou mais `Entries`
- a soma dos `amount` das entries da mesma transação deve ser sempre zero
- o saldo contábil é a soma das entries por `LedgerAccount`

### Entidades principais

#### LedgerAccount

`LedgerAccount` representa onde o crédito vive conceitualmente. Ela tem um `type` contábil e pode ter um `instrument_kind` operacional.

- `type` responde como a conta se comporta contabilmente
- `instrument_kind` responde como a conta se manifesta operacionalmente quando isso importa para o fluxo
- o projeto hoje trabalha com `BANK_ACCOUNT`, `CREDIT_CARD` e `WALLET` como instrument kinds

#### Transaction

`Transaction` não carrega moeda própria. Ela carrega identidade, data efetiva, título, descrição, status e entries subordinadas.

Os status da v1 são:

- `PENDING`
- `POSTED`
- `VOIDED`

Transições permitidas:

- `PENDING -> POSTED`
- `PENDING -> VOIDED`

Regras importantes:

- `POSTED` é um fato contábil imutável
- `VOIDED` é terminal
- não existe `POSTED -> VOIDED`
- correção de transação `POSTED` deve acontecer por nova transação de reversão, nunca por mutação destrutiva do status

#### Entry

Cada `Entry` possui pelo menos:

- `ledger_account_id`
- `amount` como `Decimal`
- `currency_id`
- `statement_closing_date` e `statement_due_date` opcionais

Regras importantes:

- `amount` é sempre assinado
- `amount` nunca deve ser `float`
- toda referência a moeda acontece por ID
- se os campos de fatura estiverem preenchidos, a conta precisa ser `LIABILITY` com `instrument_kind == CREDIT_CARD`
- `statement_closing_date` e `statement_due_date` devem aparecer juntos ou ambos devem ser `NULL`
- `statement_due_date` precisa ser maior que `statement_closing_date`

#### Tag

`Tag` é classificação flexível para organização e busca. Ela não reescreve fato contábil, não altera saldo e não substitui taxonomia contábil do core.

#### Currency

O catálogo de moedas é tratado como entidade própria. A identidade monetária do sistema vive em `Entry.currency_id`, não em `Transaction` e não em `LedgerAccount`.

### Balanços por moeda

`LedgerAccount` não possui moeda fixa de apresentação. Leituras da conta expõem `balances[]` por moeda, cada item identificado por `currency_id`.

## Arquitetura

O projeto segue arquitetura hexagonal com direção de dependência controlada:

```text
Adapter/Input -> Port/Input -> UseCase -> Domain -> Port/Output -> Adapter/Output
```

### Camadas

#### `src/core`

Contém o núcleo de negócio:

- `domain/`: estruturas de negócio e erros de domínio
- `ports/`: contratos de entrada e saída possuídos pelo core
- `usecases/`: orquestração de fluxos, regras de aplicação e tradução de erros técnicos para erros de negócio
- `shared/`: primitivas pequenas, estáveis e agnósticas de tecnologia

Regras importantes:

- o core não conhece FastAPI, SQLAlchemy, Postgres ou detalhes de infraestrutura
- regras de negócio cruzando agregados pertencem aos use cases
- `src/core/shared/` não é depósito genérico de helpers; use apenas para blocos realmente transversais

#### `src/adapters`

Traduz entre contratos externos e o core.

- `src/adapters/input/` recebe HTTP, valida entrada, chama input ports e traduz erros/respostas
- `src/adapters/output/` é reservado para adaptadores dirigidos quando a camada for útil

Regras importantes:

- rotas HTTP devem depender de input ports, não de use cases concretos
- handlers devem ser finos
- conversões devem ser explícitas

#### `src/infra`

Contém tecnologia concreta e runtime:

- bootstrap e composition root
- app FastAPI
- Postgres/SQLAlchemy
- logging
- security
- settings

`src/infra/bootstrap.py` é o composition root principal. `src/infra/main.py` constrói o app FastAPI através do container montado no bootstrap.

## Limites arquiteturais protegidos por teste

`tests/architecture/test_boundaries.py` usa `pytestarch` para garantir regras como:

- `core` não importa `adapters` nem `infra`
- `core.domain` não importa `ports`, `usecases`, `adapters` ou `infra`
- `ports` não importam `usecases`, `adapters` ou `infra`
- `usecases` não importam `adapters` nem `infra`
- `adapters` não importam `infra`
- `adapters.input` não importam `core.usecases`
- `adapters.output` não importam `core.usecases` nem `adapters.input`
- `infra.fastapi` não importa `adapters.output`
- `core.shared` não importa `adapters` nem `infra`

O prefixo de módulo usado no pytestarch deriva do nome da pasta do repositório: `Finance-Manager.src`.

## Organização do repositório

```text
Finance-Manager/
|-- alembic/
|   `-- versions/
|-- docker/
|   |-- dev/
|   `-- prd/
|-- logs/
|-- src/
|   |-- adapters/
|   |   `-- input/api/
|   |       |-- routes/
|   |       `-- schemas/
|   |-- core/
|   |   |-- domain/
|   |   |-- ports/
|   |   |   |-- input/
|   |   |   `-- output/
|   |   |-- shared/
|   |   `-- usecases/
|   `-- infra/
|       |-- bootstrap.py
|       |-- exchange_rate/
|       |-- fastapi/
|       |-- logging/
|       |-- postgres/
|       |-- security/
|       `-- settings/
|-- tests/
|   |-- architecture/
|   |-- integration/
|   `-- unit/
|-- Makefile
|-- README.md
|-- instructions.md
`-- notes.md
```

### Organização do Postgres

O Postgres segue organização orientada a aggregate dentro de `src/infra/postgres/aggregates/`.

Padrão esperado:

- uma pasta por aggregate de domínio
- modelos físicos em `models/`
- arquivos de modelo nomeados pela tabela fisica
- repositório do aggregate em `repository.py`

Exemplo de padrão:

- `src/infra/postgres/aggregates/user/models/users.py`
- `src/infra/postgres/aggregates/user/repository.py`

## Nomenclatura e estilo de código

O projeto prefere nomes explícitos, previsíveis e pouco "espertos". A meta é que o papel arquitetural de um tipo fique claro pelo nome.

### Nomeação principal

- entidades e conceitos de domínio usam nome singular: `User`, `Tag`, `Transaction`
- DTOs de entrada do domínio usam `Create*Data` e `Update*Data`
- objetos finais enviados a output ports usam `New*` e `*Changes`
- casos de uso usam o sufixo `UseCase`
- contratos do core usam `InputPort` e `OutputPort`
- exceções usam o sufixo `Error`
- doubles de teste fixos usam `Stub`
- modelos SQLAlchemy usam o sufixo `Record`
- arquivos de model dentro de `models/` usam o nome da tabela fisica

Exemplos:

- `CreateUserData -> NewUser`
- `UpdateUserData -> UserChanges`
- `UserUseCase`
- `PasswordHasherOutputPort`
- `UserEmailConflictError`
- `UserRecord`

### Vocabulário preferido

- prefira nomes sem ambiguidade entre domínio, transporte e infraestrutura
- prefira `tie_break_*` para vocábulos de ordenação secundária determinística
- prefira f-strings a `.format()`
- use `dataclass` para portadores internos simples
- use Pydantic quando parsing, validação ou serialização forem parte real da responsabilidade

### Convenções de implementação

- prefira a menor mudança que corrige a causa real no ponto que possui a responsabilidade
- não extraia abstração compartilhada na primeira duplicação sem necessidade clara
- mantenha mapeamentos importantes explícitos
- não esconda regra de negócio relevante atrás de helpers opacos
- ao tocar classes com helpers privados, prefira deixar métodos `_...` logo após `__init__` e antes dos métodos públicos

## Regras por camada

### Domain

- estruturas de negócio e erros agnósticos de tecnologia
- não importa framework, banco ou infra
- enums fechados possuídos pelo core devem permanecer tipados

### Use cases

- orquestram regras e colaborações
- traduzem `*OutputPortError` em erros de domínio/aplicação
- definem fronteiras transacionais via Unit of Work
- são o lugar certo para invariantes de negócio cruzando agregados

### Adapters HTTP

- validam entrada
- chamam input ports
- traduzem erros conhecidos para `HTTPException`
- mapeiam resposta para schemas HTTP

### Repositórios

- são session-bound
- podem fazer `flush()` e `refresh()`
- não fazem `commit()` nem `rollback()`
- retornam `None` em leituras por ausência quando apropriado
- falhas de persistência relevantes devem emergir como `*OutputPortError`

## Unit of Work, persistência e banco

### Fronteira transacional

O core não abre sessão de banco diretamente. Ele depende de `UnitOfWorkOutputPortFactory` e trabalha pelos repositórios expostos pela unidade de trabalho ativa.

Implicações:

- o use case e dono da fronteira transacional
- a implementacao concreta do UoW vive na infra
- repositórios não devem assumir commit
- se um aggregate participa da mesma transacao, ele precisa aparecer no contrato `UnitOfWorkOutputPort` e no `SQLAlchemyPostgresUnitOfWork`

### Campos persistidos compartilhados

`PostgresPersistedRecordMixin` centraliza:

- `id`
- `created_at`
- `updated_at`
- `is_deleted`
- `deleted_at`

Regras importantes:

- `updated_at` e `deleted_at` são database-owned
- soft delete é comportamento padrão
- hard delete deve ser opt-in explícito

### Constraints e erros de persistência

Quando a falha de banco carrega significado de negócio, use nomes de constraint estáveis e explícitos. A tradução deve acontecer na borda de persistência, emitindo `*OutputPortError`, e a tradução final para erro de negócio acontece no use case.

### Migrations

As migrations vivem em `alembic/versions/` e, neste momento, seguem a cadeia monótona:

- `20250502_000001_baseline.py`
- `20260502_000002_create_users.py`
- `20260510_000003_create_tags.py`
- `20260510_000004_create_ledger_accounts.py`
- `20260511_000005_create_transactions.py`
- `20260518_000006_create_currencies.py`
- `20260519_000007_create_entries.py`
- `20260519_000008_create_entry_tags.py`
- `20260519_000009_seed_test_data.py`

Ao editar migrations:

- preserve cadeia monótona simples
- use nomes claros e ordenados
- valide `upgrade head`
- não crie forks desnecessários na história do Alembic

## Convenções de API

### Regras gerais

- rotas dependem de input ports
- respostas HTTP não devem expor detalhes de persistência
- dados sensíveis, como senha e hash de senha, nunca vazam em response schemas
- enums de contrato público pertencem ao adapter/schema, não ao domínio

### Mapeamento de erros

Use o significado semântico da falha:

- `404` para recurso ausente
- `409` para conflito de estado ou unicidade
- `422` para payload sintaticamente válido que viola regra de negócio

### Paginação e ordenação

O projeto separa a responsabilidade de listagem por camada:

- `src/core/shared/listing.py`: `ListQuery`, `SortTerm`, `Page[T]`
- `src/adapters/input/api/pagination.py`: parser HTTP
- `src/adapters/input/api/schemas/pagination_schema.py`: `PageResponse[T]`
- `src/infra/postgres/listing.py`: tradução para `ORDER BY`

Regras importantes:

- `offset`, `limit` e `sort` são o contrato atual
- o adapter decide whitelist de campos ordenáveis
- o repositório não deve inventar ordenação default silenciosa
- respostas paginadas devem incluir `items`, `offset`, `limit` e `total`

### Rotas CRUD

O padrão atual de recursos HTTP é:

- prefixo singular por recurso
- endpoint base para operações individuais
- `/list` para coleções paginadas

Exemplos:

- `/user` e `/user/list`
- `/currency` e `/currency/list`
- `/transaction` e `/transaction/list`

Quando o recurso suporta soft delete, `hard_delete=true` é o gatilho explícito para remoção física.

## Logging, settings e runtime

### Settings

`src/infra/settings/models.py` é a fonte de verdade para configuração. Evite espalhar defaults operacionais em rotas, use cases ou infra solta.

Categorias atuais:

- `environment`
- `log`
- `fastapi`
- `postgres`

No desenvolvimento, as settings são carregadas a partir de `docker/dev/.env`.

### Logging

Logging é configurado em `src/infra/logging/` e acionado na criação do app FastAPI. Não replique configuração ad-hoc em outros pontos do projeto.

## Security e hashing

Hash de senha é exposto ao core por `PasswordHasherOutputPort`.

Padrão atual:

- implementação concreta: `ScryptPasswordHasher`
- formato persistido: `scrypt$n=16384$r=8$p=1$dklen=64$salt$hash`
- verificação deve ser resistente a timing attack
- formato legado `scrypt$salt$hash` não é suportado

## Testes e qualidade

### Estrutura da suíte

- `tests/unit/`: testes isolados por módulo
- `tests/integration/fastapi/`: colaboração real na superfície HTTP
- `tests/integration/postgres/`: persistência e infraestrutura real
- `tests/architecture/`: proteção dos limites arquiteturais

Os testes devem espelhar a estrutura da aplicação quando a fronteira faz sentido.

### Convenções de teste

- prefira nomes comportamentais como `test_<acao>_<resultado>_<condicao>`
- suítes análogas devem afirmar comportamento com profundidade semelhante
- use `Stub` para doubles fixos
- `conftest.py` deve cuidar de composição e ciclo de fixtures, não virar depósito de builders

### Helpers compartilhados de teste

Convenções atuais relevantes:

- builders compartilhados de FastAPI vivem em `tests/integration/fastapi/helpers/builders.py`
- stubs compartilhados de FastAPI vivem em `tests/integration/fastapi/helpers/stubs.py`
- suítes unitárias CRUD de rota devem preferir esses helpers em vez de recriar payloads e doubles locais sem necessidade
- helpers compartilhados de Postgres ficam em `tests/integration/postgres/helpers/`

### Barra de qualidade

- cobertura exigida: `100%` sobre `src/`
- branch coverage também é obrigatória
- lint: Ruff
- type checking: MyPy

Comandos principais:

```bash
make run-tests
make run-tests-with-coverage
make run-quality-check
```

## Comandos operacionais

### Desenvolvimento local

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r docker/dev/requirements.txt
make run-database
make run-migrations
make run-api
```

### Validação

```bash
make run-tests
make run-tests-with-coverage
make run-quality-check
```

### Runtime local relevante

- API local: `http://localhost:8000`
- docs: `http://localhost:8000/docs`
- openapi: `http://localhost:8000/openapi.json`

## Armadilhas recorrentes

Ao trabalhar neste repositório, evite:

- colocar regra de negócio em rota HTTP
- deixar o core importar adapters ou infra
- abrir sessão de banco fora do Unit of Work quando o fluxo já pertence a um use case transacional
- introduzir referência textual onde a regra atual exige referência por ID
- reintroduzir moeda na `Transaction` ou moeda fixa em `LedgerAccount`
- mutar transação `POSTED` como se fosse CRUD livre
- tratar `Tag` como categoria contábil rígida
- criar docs públicas no README com nível de detalhe interno que deveria morar aqui
- assumir que `notes.md` é fonte oficial sem conferir o código

## Checklist antes de editar o código

1. Confirmar a responsabilidade da camada dona do comportamento.
2. Identificar se o contrato público muda.
3. Se mudar contrato público, atualizar `README.md` quando fizer sentido e revisar schemas/rotas.
4. Manter alinhamento com nomenclatura canônica do repositório.
5. Adicionar ou ajustar testes na menor superfície capaz de provar o comportamento.
6. Rodar ao menos validação focada antes de ampliar escopo.
7. Fechar com `make run-quality-check` e, quando a mudança justificar, `make run-tests-with-coverage`.

## Fonte de verdade preferida

Quando houver tensão entre documentos, prefira esta ordem:

1. código atual e testes
2. settings, Makefile e rotas reais
3. `instructions.md`
4. `README.md`
5. `notes.md`

Se `notes.md` divergir do código, trate a divergência como contexto histórico ou backlog, não como contrato vigente.