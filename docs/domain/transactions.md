# Transactions, Entries e FX

Esta é a parte mais sensível do domínio hoje. Ela merece um documento próprio porque a semântica de transaction é deliberadamente assimétrica entre input, aplicação, persistência e output.

## O que entra no sistema

No contrato de escrita HTTP e no tipo `NewEntry`, cada entry recebe:

- `ledger_account_id`
- `amount` na moeda de origem
- `currency_id`
- datas factuais de fatura quando aplicável
- tags opcionais

O contrato de escrita não recebe `amount_in_dollars`.

## O que a aplicação calcula

`src/core/usecases/transaction_usecase.py` resolve a taxa de câmbio para dólar via `ExchangeRateOutputPort` e enriquece cada entry com:

- `amount_in_dollars`
- `planned_exchange_rate_to_dollars`
- `posting_exchange_rate_to_dollars`

O cálculo atual de dólar é quantizado em centavos (`0.01`).

## Lifecycle monetário atual

### Create ou update em `PENDING`

- a aplicação captura `planned_exchange_rate_to_dollars`;
- calcula `amount_in_dollars` com base no `amount` original;
- valida o balanceamento em dólar;
- persiste a transaction ainda sem taxa final de posting.

### Create já em `POSTED`

- a aplicação primeiro captura a taxa planejada;
- depois captura também a taxa final de posting;
- recalcula `amount_in_dollars` com a taxa final antes de persistir.

### `post_transaction(...)`

- a aplicação parte do valor-base persistido e da taxa planejada para rederivar o valor original;
- captura a taxa final de posting;
- recalcula `amount_in_dollars`;
- valida novamente o balanceamento;
- persiste a transaction já postada com o snapshot final.

## O que é persistido e lido

Na persistência de `entries`, o sistema grava hoje:

- `currency_id`
- `amount_in_dollars`
- `planned_exchange_rate_to_dollars`
- `posting_exchange_rate_to_dollars`
- `statement_closing_date`
- `statement_due_date`

O `amount` original não é persistido.

## O que sai na API

Nas responses de leitura, a API expõe:

- `amount_in_dollars`
- `currency_id`
- `planned_exchange_rate_to_dollars`
- `posting_exchange_rate_to_dollars`
- datas factuais de fatura

Essa assimetria é intencional: escrever em moeda de origem é mais ergonômico; ler e persistir em dólar mantém a semântica contábil-base estável.

## Regras invariantes que não devem regredir

- `PENDING` significa “ainda não postada”, não “futura”.
- `POSTED` e `VOIDED` continuam terminais.
- O balanceamento da transaction é validado em dólar.
- `currency_id` continua representando a moeda original da entry.
- `LedgerAccount.balances[]` continua semanticamente por moeda, não por dólar-base.
- Não reintroduza persistência do `amount` original só para facilitar posting.

## Arquivos canônicos

- `src/core/domain/transaction.py`
- `src/core/usecases/transaction_usecase.py`
- `src/adapters/input/api/schemas/transaction_schema.py`
- `src/infra/postgres/aggregates/transaction/models/entries.py`