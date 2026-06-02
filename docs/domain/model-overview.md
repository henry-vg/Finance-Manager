# Modelo de Domínio

O Finance Manager continua sendo uma API de gestão financeira baseada em contabilidade de dupla entrada. A modelagem do domínio prioriza rastreabilidade, limites explícitos e previsibilidade operacional.

## Princípio central

- `Transaction` representa o evento contábil.
- `Entry` representa o efeito desse evento sobre saldos.
- Toda `Transaction` tem duas ou mais `Entries`.
- `LedgerAccount` representa onde o crédito vive conceitualmente.
- `Tag` classifica; não redefine fato contábil.
- `Currency` vive no catálogo e é referenciada por ID.

## Entidades principais

### LedgerAccount

`LedgerAccount` combina identidade, timestamps, `type`, `instrument_kind` e `balances[]`.

- `type` responde como a conta se comporta contabilmente.
- `instrument_kind` responde como a conta aparece operacionalmente quando isso importa.
- Os balances são expostos por moeda, cada item identificado por `currency_id`.

### Transaction

`Transaction` carrega identidade, timestamps, `effective_at`, título, descrição, status e entries subordinadas.

Os status atuais são:

- `PENDING`
- `POSTED`
- `VOIDED`

As transições suportadas continuam sendo:

- `PENDING -> POSTED`
- `PENDING -> VOIDED`

`POSTED` e `VOIDED` são terminais.

### Entry

`Entry` continua sendo a unidade factual do efeito contábil. A semântica monetária atual está separada em dois níveis:

- no contrato de escrita, a entry recebe `amount` na moeda de origem e `currency_id`;
- internamente e na persistência, o sistema trabalha com `amount_in_dollars` e snapshots cambiais.

As regras detalhadas desta assimetria ficam em `transactions.md`.

### Tag

`Tag` é classificação flexível. Ela não substitui taxonomia contábil rígida, não altera saldo e não reescreve fatos históricos.

### Currency

O catálogo de moedas é tratado como entidade própria. A identidade monetária da operação vive na entry e não na transaction como um todo.

## Invariantes importantes

- Toda referência a outra entidade acontece por ID.
- `amount` de entrada é sempre `Decimal`; nunca `float`.
- `statement_closing_date` e `statement_due_date` aparecem juntos ou ambos são `NULL`.
- Se os campos de fatura estiverem preenchidos, a entry precisa apontar para conta `LIABILITY` com `instrument_kind == CREDIT_CARD`.
- `statement_due_date` precisa ser maior que `statement_closing_date`.
- `LedgerAccount` não tem moeda fixa de apresentação; os balances continuam por moeda.

## Arquivos canônicos

- `src/core/domain/ledger_account.py`
- `src/core/domain/transaction.py`
- `src/core/domain/currency.py`
- `tests/unit/core/`