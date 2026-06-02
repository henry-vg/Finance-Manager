# Auditoria tecnica completa do MVP

## Escopo revisado

Auditoria tecnica realizada a partir de leitura estatica do repositorio, sem alteracao de codigo executavel.

Fontes revisadas:

- `.cursor/rules/`
- `docs/README.md`
- `docs/meta/project-context.md`
- `docs/meta/current-state.md`
- `docs/architecture/`
- `docs/domain/`
- `docs/api/`
- `docs/persistence/`
- `docs/testing/`
- `docs/operations/`
- `README.md`
- `Makefile`
- `pyproject.toml`
- `src/core/`
- `src/adapters/input/api/`
- `src/infra/`
- `src/infra/postgres/`
- `alembic/versions/`
- `tests/architecture/`
- `tests/unit/`
- `tests/integration/fastapi/`
- `tests/integration/postgres/`

## Metodologia

- Comparacao entre documentacao canonica, codigo atual e testes.
- Revisao de regras de dominio, fronteiras arquiteturais, persistencia, API, UoW e testes.
- Classificacao dos achados por impacto potencial:
  - **Critico**: risco de falha grave de corretude, seguranca ou operacao em uso real.
  - **Alto**: risco relevante de comportamento incorreto, regressao dificil ou contrato enganoso.
  - **Medio**: inconsistencia, divida ou lacuna com impacto controlado, mas relevante para evolucao.
  - **Baixo**: melhoria de clareza, documentacao, manutencao ou alinhamento.

## Sumario por severidade

- Critico: 0 achados confirmados.
- Alto: 4 achados.
- Medio: 8 achados.
- Baixo: 5 achados.

## Achados criticos

Nenhum achado critico confirmado nesta auditoria estatica.

Nao foi identificado, no escopo atual, bug evidente que comprometa imediatamente a integridade basica das transactions persistidas dentro dos fluxos cobertos. Os riscos mais importantes estao classificados como altos por dependerem do uso real do sistema, de escopo de produto ainda nao implementado ou de contratos parcialmente enganosos.

## Achados altos

### ALTO-01 - `LedgerAccount.balances[]` e documentado/exposto, mas nao e calculado

**Categoria:** problema de modelagem, inconsistencia, documentacao potencialmente desatualizada.

**Evidencias:**

- `docs/domain/model-overview.md` descreve balances por moeda em `LedgerAccount`.
- `docs/domain/product-decisions.md` reforca que `LedgerAccount` nao tem moeda fixa e expoe `balances[]`.
- `src/core/domain/ledger_account.py` define `LedgerAccountBalance` e `LedgerAccount.balances`.
- `src/adapters/input/api/schemas/ledger_account_schema.py` expoe `balances` na response.
- `src/infra/postgres/aggregates/ledger_account/repository.py` monta `LedgerAccount` sem preencher balances, portanto usa o default `()`.

**Impacto:**

Consumidores da API podem acreditar que saldos estao disponiveis e confiaveis, quando na pratica a resposta real tende a trazer sempre lista vazia. Isso afeta uma API financeira, onde saldo e informacao central.

**Risco:**

Alto risco de decisao de produto/cliente baseada em contrato enganoso. Tambem pode mascarar ausencia de calculo de saldo em testes se a suite nao afirmar balances reais.

**Recomendacao:**

Decidir explicitamente entre:

1. implementar calculo de balances por moeda; ou
2. documentar que `balances[]` e placeholder ainda nao implementado; ou
3. remover/ocultar temporariamente o campo do contrato publico se ainda nao for suportado.

Se a decisao alterar contrato publico ou dominio, atualizar `docs/domain/model-overview.md`, `docs/domain/product-decisions.md`, `docs/api/http-conventions.md` e testes.

### ALTO-02 - Ausencia de autenticacao/autorizacao apesar de existir modelo de usuario com senha

**Categoria:** problema de modelagem, risco de seguranca, documentacao potencialmente incompleta.

**Evidencias:**

- `src/core/domain/user.py` possui `password_hash`.
- `src/infra/security/password_hasher.py` implementa scrypt.
- `src/core/usecases/user_usecase.py` faz hash de senha em create/update.
- Nao ha login, token, middleware de autenticacao, autorizacao por recurso ou sessao.
- Rotas FastAPI em `src/adapters/input/api/routes/` nao exigem credenciais.

**Impacto:**

Em ambiente exposto, todos os endpoints de dados financeiros ficam abertos. O sistema tem aparencia de suportar usuario e senha, mas isso ainda nao protege a API.

**Risco:**

Alto se o MVP for executado fora de ambiente local/controlado. Mesmo como MVP, a existencia de senha hasheada pode levar mantenedores a inferir erroneamente que ha camada de auth.

**Recomendacao:**

Registrar explicitamente em `docs/meta/current-state.md` e/ou documentacao de produto que autenticacao/autorizacao esta fora do escopo atual. Quando implementada, preservar a fronteira hexagonal com ports para autenticacao e evitar acoplar regras de auth diretamente nas rotas.

### ALTO-03 - Ausencia de tenancy/ownership entre usuarios e dados financeiros

**Categoria:** problema de modelagem, risco de evolucao, possivel inconsistencia de produto.

**Evidencias:**

- `users` existe como aggregate independente.
- `ledger_accounts`, `tags`, `transactions`, `entries` e `currencies` nao possuem `user_id`.
- Use cases e ports nao recebem contexto de usuario.
- API opera sobre IDs globais.

**Impacto:**

O sistema e descrito como gestao financeira pessoal, mas o modelo atual e efetivamente single-tenant. Qualquer evolucao para multiusuario exigira mudancas transversais em dominio, ports, use cases, schemas, repositorios, migrations, testes e possivelmente dados historicos.

**Risco:**

Alto risco de refatoracao cara se o produto precisar isolar dados por usuario depois de uso real. Tambem aumenta o risco de vazamento caso autenticacao seja adicionada sem ownership nos aggregates.

**Recomendacao:**

Registrar decisao explicita: single-tenant no MVP ou multi-tenant planejado. Se multi-tenant for requisito, tratar como expansao arquitetural com ADR e plano de migration.

### ALTO-04 - Barra de coverage configurada em 100%, mas snapshot documenta falha em 99.62%

**Categoria:** gap de testes, risco operacional.

**Evidencias:**

- `pyproject.toml` define `fail_under = 100` e branch coverage.
- `docs/meta/current-state.md` registra que `make run-tests-with-coverage` executou 405 testes, mas falhou com `99.62%`.
- Misses documentados em `src/core/usecases/transaction_usecase.py` e `src/infra/postgres/aggregates/transaction/repository.py`.

**Impacto:**

A barra oficial do projeto pode falhar em validacao ampla. Isso cria atrito para mudancas futuras e pode induzir agentes/mantenedores a reduzir coverage indevidamente.

**Risco:**

Alto porque os misses estao nos componentes mais sensiveis do dominio: transaction use case e repository.

**Recomendacao:**

Adicionar testes focados para os branches faltantes em transaction e repository. Nao reduzir `fail_under` sem decisao explicita.

## Achados medios

### MEDIO-01 - Regras de lifecycle de transaction aparecem tanto no use case quanto no repositorio

**Categoria:** risco de manutencao, fronteira arquitetural conceitual.

**Evidencias:**

- `src/core/usecases/transaction_usecase.py` valida status antes de update/post/void.
- `src/infra/postgres/aggregates/transaction/repository.py` tambem valida `TransactionStatus.PENDING` e transicoes via `can_transition_transaction_status`.
- O repositorio levanta erros de dominio como `TransactionMustBePendingError` e `TransactionStatusTransitionNotAllowedError`.

**Impacto:**

Duplicacao de regra aumenta risco de divergencia. Apesar de nao violar os testes de import atuais, a infra passa a conhecer semantica de dominio alem da persistencia.

**Risco:**

Medio. Pode ser justificavel como protecao contra corrida/concorrrencia, mas precisa ser tratado como invariante duplicada intencional.

**Recomendacao:**

Documentar a duplicacao como defesa transacional ou concentrar a traducao em erros de output port. Se mantida, garantir testes que cubram concorrencia/estado stale.

### MEDIO-02 - Update de transaction apaga fisicamente entries antigas

**Categoria:** modelagem, persistencia, rastreabilidade.

**Evidencias:**

- `EntryRecord` herda `PostgresPersistedRecordMixin`, com `is_deleted` e `deleted_at`.
- `SQLAlchemyTransactionRepository._replace_entries(..., purge_existing=True)` usa `session.delete(entry_record)` para entries antigas.
- `entry_tags` tem `ondelete="CASCADE"`.

**Impacto:**

Historico fisico das entries substituidas e perdido em update. Para dominio financeiro, rastreabilidade de alteracoes pode ser requisito futuro.

**Risco:**

Medio. O comportamento pode ser correto para MVP se transaction pendente for rascunho, mas contrasta com a presenca de soft delete no mixin.

**Recomendacao:**

Explicitar na documentacao de transaction/persistencia que update de transaction pendente substitui entries fisicamente, ou alterar para soft delete quando a rastreabilidade virar requisito.

### MEDIO-03 - Transaction possui campos de soft delete, mas lifecycle publico usa void e nao delete

**Categoria:** inconsistencia, risco de manutencao.

**Evidencias:**

- `transactions` herda campos `is_deleted` e `deleted_at`.
- `TransactionOutputPort` nao possui delete.
- API nao tem `DELETE /transaction`.
- Lifecycle usa `void`.

**Impacto:**

Mantenedores podem assumir que transaction segue o padrao CRUD com soft/hard delete, como os demais recursos. Na pratica, o aggregate usa invalidacao de dominio.

**Risco:**

Medio. Confusao de evolucao pode levar a endpoints de delete indevidos para fatos contabeis.

**Recomendacao:**

Documentar explicitamente que transaction nao suporta delete publico no MVP; `VOIDED` e a operacao de anulacao semantica.

### MEDIO-04 - Criacao direta de transaction `VOIDED` e permitida, mas pouco documentada

**Categoria:** inconsistencia documental, regra de dominio ambigua.

**Evidencias:**

- `CreateTransactionData.status` aceita `TransactionStatus`.
- `TransactionUseCase.create_transaction` permite `VOIDED`.
- Testes unitarios cobrem `test_create_transaction_allows_voided_historical_transaction`.
- Docs enfatizam `PENDING -> VOIDED`, mas nao destacam a criacao direta como `VOIDED`.

**Impacto:**

Ambiguidade entre lifecycle operacional e importacao/historico. Pode afetar consumidores da API e futuros validadores.

**Risco:**

Medio. Se criacao direta como `VOIDED` for intencional para historico, precisa ser canonica; se nao for, e uma brecha de regra.

**Recomendacao:**

Decidir e documentar. Se for importacao/historico, explicar em `docs/domain/transactions.md`; se nao, restringir create a estados permitidos.

### MEDIO-05 - Recalculo de posting depende de rederivar `amount` original por taxa planejada

**Categoria:** risco de corretude monetaria.

**Evidencias:**

- `TransactionUseCase._to_entry_for_posting` calcula `amount = amount_in_dollars / planned_rate`.
- O `amount` original nao e persistido por decisao documentada.
- `_to_dollar_amount` quantiza em `0.01`.

**Impacto:**

Dependendo de moedas, casas decimais e arredondamentos, o valor rederivado pode nao corresponder exatamente ao input original. Isso pode afetar o recalculo com taxa de posting.

**Risco:**

Medio. A decisao e intencional, mas permanece sensivel em cenario real com moedas de precisao diferente, criptoativos ou taxas variaveis.

**Recomendacao:**

Adicionar testes com moedas de diferentes precisions e taxas que gerem arredondamento. Documentar claramente o trade-off em `docs/domain/transactions.md`.

### MEDIO-06 - Adapter cambial mock limita comportamento real de currencies

**Categoria:** risco operacional, gap funcional conhecido.

**Evidencias:**

- `src/infra/exchange_rate/mock_exchange_rate_adapter.py` possui TODO para provider real.
- Taxas mock cobrem `USD`, `BRL`, `EUR`, `BTC`.
- Currencies podem ser cadastradas livremente, mas transactions com moeda sem taxa mock falham.

**Impacto:**

Catalogo de moedas aceita mais valores do que o motor de transactions consegue processar.

**Risco:**

Medio. Documentado como debito conhecido, mas pode surpreender usuarios da API.

**Recomendacao:**

Enquanto nao houver provider real, documentar claramente as moedas transacionaveis no MVP ou validar disponibilidade de FX ao criar currency.

### MEDIO-07 - `User` e tratado por email na API enquanto outros recursos usam id

**Categoria:** inconsistencia de contrato publico.

**Evidencias:**

- `UserInputPort.get_user(email)` e `update_user(current_email, ...)`.
- `GET /user`, `PUT /user`, `DELETE /user` usam email/current_email.
- Demais recursos usam `id`.

**Impacto:**

Email passa a ser identificador publico mutavel. Update de email precisa de parametro `current_email` e payload com novo email, criando assimetria operacional.

**Risco:**

Medio. Pode ser intencional, mas merece documentacao explicita para evitar mudancas ad hoc.

**Recomendacao:**

Registrar a decisao em `docs/api/http-conventions.md` ou alinhar User ao padrao por id em uma mudanca planejada.

### MEDIO-08 - Integracao Postgres pode ser pulada silenciosamente se banco nao estiver disponivel

**Categoria:** gap de testes, risco de CI/local.

**Evidencias:**

- `tests/integration/postgres/conftest.py` usa `pytest.skip` se a conexao falhar.
- Isso e conveniente localmente, mas pode esconder ausencia de banco na validacao se CI nao tratar skips.

**Impacto:**

Uma execucao de testes pode passar sem exercitar persistencia real.

**Risco:**

Medio. Em projeto com regras fortes de persistencia, skips precisam ser visiveis e controlados.

**Recomendacao:**

Definir politica de CI: Postgres obrigatorio em pipeline completo; skip apenas para execucao local sem banco.

## Achados baixos

### BAIXO-01 - Pasta `src/adapters/output/` vazia pode confundir leitura arquitetural

**Categoria:** documentacao/manutencao.

**Evidencias:**

- A arquitetura conceitual menciona `Adapter/Output`.
- Implementacoes concretas estao em `src/infra/`.
- `src/adapters/output/` existe sem implementacoes.

**Impacto:**

Baixo, pois os testes de boundaries aceitam a estrutura atual. Ainda assim, novos mantenedores podem procurar output adapters no local errado.

**Recomendacao:**

Adicionar nota curta em `docs/architecture/hexagonal-architecture.md` explicando que adapters concretos de saida vivem em `infra` neste projeto.

### BAIXO-02 - ADRs ainda inexistentes para decisoes duraveis relevantes

**Categoria:** documentacao historica.

**Evidencias:**

- `docs/adr/README.md` informa que ainda nao ha ADRs.
- Decisoes como transaction assimetrica, FX base em dolar, ausencia de persistencia de amount original e UoW sao duraveis.

**Impacto:**

Racional historico pode se perder, embora documentos tematicos estejam bons.

**Risco:**

Baixo a medio, dependendo da rotatividade de mantenedores.

**Recomendacao:**

Criar ADRs apenas quando houver mudanca nova ou revisao explicita dessas decisoes, para evitar burocracia retroativa excessiva.

### BAIXO-03 - `current-state.md` registra lacuna de coverage, mas nao indica se e estado ainda vigente

**Categoria:** documentacao potencialmente desatualizada.

**Evidencias:**

- `docs/meta/current-state.md` registra uma validacao especifica com 405 testes e 99.62%.
- Nao ha timestamp/commit da execucao alem do contexto do snapshot.

**Impacto:**

Leitores podem nao saber se o gap ainda existe.

**Risco:**

Baixo. A informacao ainda e util, mas pode envelhecer.

**Recomendacao:**

Ao proximo ciclo de validacao ampla, atualizar o snapshot com resultado atual e contexto.

### BAIXO-04 - Contrato de `Currency.storage_decimal_places` e exposto sem racional detalhado

**Categoria:** documentacao de dominio/API.

**Evidencias:**

- `Currency.storage_decimal_places` retorna `decimal_places + 1`.
- `CurrencyResponse` expoe esse campo.
- A documentacao canonica nao explica claramente a regra.

**Impacto:**

Baixo, mas consumidores podem nao entender a finalidade do campo.

**Recomendacao:**

Documentar o significado de `storage_decimal_places` em docs de dominio ou API quando a area de currencies for tocada.

### BAIXO-05 - Logging cria diretorios em runtime

**Categoria:** operacao/manutencao.

**Evidencias:**

- `src/infra/logging/config.py` cria `Path(file_path).parent.mkdir(parents=True, exist_ok=True)` quando file logging esta habilitado.

**Impacto:**

Baixo. Conveniente em dev, mas em ambientes restritos pode falhar por permissao antes da app subir corretamente.

**Recomendacao:**

Documentar expectativa de permissao de escrita para file logging ou garantir que producao use stdout quando apropriado.

## Gaps de testes observados

- Testes para `LedgerAccount.balances[]` reais nao existem porque o comportamento nao esta implementado.
- Tests de transaction cobrem muitas regras, mas o snapshot indica branches ainda descobertos em `transaction_usecase.py` e repository.
- Pouca evidencia de testes para cenarios monetarios com arredondamentos mais agressivos, moedas com diferentes casas decimais e taxas nao triviais.
- Integracao Postgres pode ser pulada quando o banco nao esta disponivel; isso precisa ser controlado em CI.
- Auth/tenancy nao tem testes porque nao existe no MVP.

## Violacoes arquiteturais

Nenhuma violacao dos boundaries automatizados foi identificada na leitura.

Observacao conceitual: `SQLAlchemyTransactionRepository` conhece e levanta erros de dominio relacionados a lifecycle. Isso nao quebra os testes atuais, mas e um ponto de atencao de ownership: se for uma defesa contra corrida, deve ser documentada como regra intencional da persistencia transacional.

## Documentacao potencialmente desatualizada ou incompleta

- `LedgerAccount.balances[]` aparece como capacidade atual, mas nao ha calculo real.
- Criacao direta de transaction `VOIDED` existe em testes/codigo, mas nao esta destacada na documentacao de lifecycle.
- Auth/tenancy estao implicitamente ausentes, mas a presenca de users/senha pode confundir.
- Organizacao de output adapters poderia ser explicada melhor, ja que a pasta `adapters/output` nao contem implementacoes.

## Decisoes tomadas nesta auditoria

- Nenhuma alteracao de codigo foi feita.
- Nenhum documento canonico de arquitetura/dominio/API/persistencia foi alterado.
- Esta auditoria foi registrada como historico em `docs/audits/`, conforme regra da pasta.

## Validacao executada

- Leitura estatica dos arquivos listados no escopo.
- Confirmacao de status Git antes da edicao documental.
- Nao foram executados testes automatizados, pois a entrega e um documento de auditoria e o pedido explicitou que nao deveria haver alteracao de codigo.

## Pendencias recomendadas

1. Decidir o destino de `LedgerAccount.balances[]`: implementar, documentar como placeholder ou remover do contrato publico.
2. Explicitar no estado atual que auth e tenancy nao existem no MVP.
3. Fechar coverage dos branches pendentes em transaction.
4. Documentar ou revisar criacao direta de transaction `VOIDED`.
5. Decidir se a duplicacao de regra de lifecycle no repositorio e defesa intencional contra concorrencia.
6. Definir politica de CI para Postgres integration tests.
