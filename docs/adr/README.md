# ADRs

Esta pasta existe para receber decisões arquiteturais duráveis sem retransformar `docs/` ou qualquer documento raiz em um novo monólito.

## Quando criar uma ADR

Crie uma ADR quando a mudança:

- alterar um boundary arquitetural;
- redefinir uma convenção importante de domínio, persistência ou contrato público;
- introduzir trade-off durável que precise de racional histórico;
- afetar várias áreas do repositório e merecer referência futura explícita.

Se o conteúdo for apenas um snapshot do estado atual do MVP, use `docs/meta/current-state.md`. Se for só resultado de revisão ou auditoria, use `docs/audits/`.

## Formato sugerido

Nomeie arquivos com data e assunto, por exemplo:

- `20260602-estrutura-cursor-e-docs.md`
- `20260602-semantica-transaction-fx.md`

Cada ADR deve registrar:

- contexto;
- decisão;
- consequências;
- arquivos canônicos relacionados.

## Regra de manutenção

ADRs não substituem a documentação canônica por área. Quando uma ADR mudar entendimento vigente de arquitetura, domínio, persistência, API, testes ou operação, atualize também a página temática correspondente em `docs/`.

Prefira poucas ADRs, mas com motivação clara e consequência explícita.

## Estado atual

No momento, a pasta existe como estrutura pronta para histórico futuro, mas ainda não possui ADRs registradas.
