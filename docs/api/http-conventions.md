# Convenções HTTP

Os adapters HTTP do projeto existem para traduzir entre contrato público e core. Eles não são a casa da regra de negócio.

## Responsabilidade da camada

Em `src/adapters/input/api/`, o padrão esperado continua sendo:

- validar entrada e query params;
- converter payload para tipos do core;
- chamar input ports;
- traduzir erros conhecidos para respostas HTTP;
- mapear tipos do core para schemas públicos.

Rotas não devem importar use cases concretos.

## Semântica de erro

Use o significado da falha, não apenas a conveniência do momento:

- `404`: recurso ausente
- `409`: conflito de estado ou unicidade
- `422`: payload sintaticamente válido que viola regra de negócio

## Padrão de rotas

O padrão atual é:

- prefixo singular para o recurso individual;
- `/list` para coleções paginadas.

Exemplos atuais:

- `/user` e `/user/list`
- `/currency` e `/currency/list`
- `/ledger-account` e `/ledger-account/list`
- `/transaction` e `/transaction/list`

Quando um recurso suporta soft delete, `hard_delete=true` é o gatilho explícito para remoção física.

## Paginação e ordenação

O contrato atual separa a responsabilidade por camada:

- `src/core/shared/listing.py`: `ListQuery`, `SortTerm`, `Page[T]`
- `src/adapters/input/api/pagination.py`: parser HTTP
- `src/adapters/input/api/schemas/pagination_schema.py`: `PageResponse[T]`
- `src/infra/postgres/listing.py`: tradução para `ORDER BY`

Regras importantes:

- `offset`, `limit` e `sort` são o contrato atual.
- O adapter define a whitelist dos campos ordenáveis.
- O repositório não inventa ordenação default silenciosa.
- Respostas paginadas incluem `items`, `offset`, `limit` e `total`.

## Convenções de contrato público

- Enums públicos pertencem ao adapter/schema, não ao domínio.
- Responses não expõem detalhes sensíveis, como hash de senha.
- O contrato HTTP pode ser assimétrico em relação ao modelo interno quando isso reduz ambiguidade.

O exemplo mais importante hoje é `transaction`:

- request escreve `amount` na moeda de origem;
- response lê `amount_in_dollars` e snapshots cambiais.

## Arquivos canônicos

- `src/adapters/input/api/router.py`
- `src/adapters/input/api/routes/`
- `src/adapters/input/api/schemas/`
- `tests/integration/fastapi/routes/`