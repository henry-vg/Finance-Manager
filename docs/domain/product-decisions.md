# Decisões de Produto e Domínio

Esta página registra as decisões de produto e domínio que o Cursor precisa conhecer para não reinventar o sistema durante desenvolvimento.

## Escopo implementado hoje

O repositório cobre hoje o núcleo da aplicação:

- usuários;
- moedas;
- contas contábeis;
- tags;
- transações com entries;
- health checks e OpenAPI.

## Decisões estruturais do modelo

### Transaction é o evento; Entry é o efeito

- `Transaction` é a raiz do agregado contábil.
- `Entry` e `EntryTag` são escritas subordinadas a `Transaction`.
- `Transaction` não carrega um valor próprio; os efeitos monetários vivem nas entries.

### Transaction não tem moeda própria

- a identidade monetária da operação vive em cada `Entry`;
- `currency_id` continua sendo a referência monetária factual da entry;
- a aplicação usa dólar como base contábil interna para balanceamento e persistência atual de transactions.

### LedgerAccount não tem moeda fixa

- `LedgerAccount` não carrega moeda de apresentação fixa;
- leituras de conta expõem `balances[]` por moeda;
- `balances[]` continuam semanticamente por `currency_id`, não por dólar-base.

### Tag é classificação flexível

- `Tag` organiza, busca e agrupa;
- `Tag` não substitui taxonomia contábil rígida;
- `Tag` não altera saldo nem reescreve fato contábil.

### Cartão de crédito é modelado por dados factuais na entry

- `statement_closing_date` e `statement_due_date` vivem em `Entry`;
- esses campos só fazem sentido para contas `LIABILITY` com `instrument_kind == CREDIT_CARD`;
- no modelo atual do repositório, não existe aggregate persistido separado para “fatura”; a identidade factual da fatura continua embutida nas entries relevantes.

## Lifecycle de transaction

- `PENDING` significa “ainda não postada”;
- `POSTED` e `VOIDED` são terminais;
- as transições suportadas continuam sendo `PENDING -> POSTED` e `PENDING -> VOIDED`.

## Semântica monetária atual de transaction

O detalhe operacional está em `transactions.md`, mas as decisões centrais são:

- request de escrita recebe `amount` na moeda de origem;
- aplicação resolve `amount_in_dollars` internamente;
- persistência e leitura pública de transaction usam `amount_in_dollars` e snapshots cambiais;
- o `amount` original não é persistido.

## O que o sistema não modela como parte do núcleo atual

No estado atual do repositório, o núcleo não possui modelagem própria para:

- aggregate separado de fatura de cartão;
- reconciliação bancária;
- importação financeira automatizada;
- integrações de Open Finance;
- IA de classificação ou enriquecimento de transações.

Se uma demanda cair em uma dessas áreas, trate isso como expansão de produto e não como ajuste local do desenho atual.

## Arquivos canônicos

- `README.md`
- `src/core/domain/transaction.py`
- `src/core/domain/ledger_account.py`
- `src/core/domain/tag.py`
- `docs/domain/transactions.md`