# ADRs

Esta pasta existe para receber decisões arquiteturais duráveis sem retransformar `docs/` ou qualquer documento raiz em um novo monólito.

## Quando criar uma ADR

Crie uma ADR quando a mudança:

- alterar um boundary arquitetural;
- redefinir uma convenção importante de domínio, persistência ou contrato público;
- introduzir trade-off durável que precise de racional histórico;
- afetar várias áreas do repositório e merecer referência futura explícita.

## Formato sugerido

Nomeie arquivos com data e assunto, por exemplo:

- `20260602-estrutura-cursor-e-docs.md`
- `20260602-semantica-transaction-fx.md`

Cada ADR deve registrar:

- contexto;
- decisão;
- consequências;
- arquivos canônicos relacionados.