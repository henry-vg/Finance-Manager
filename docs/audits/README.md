# Audits

Esta pasta guarda auditorias datadas do repositório. Use-a para registrar revisões, achados, decisões locais e pendências sem transformar esses relatórios em documentação canônica do produto.

## Quando usar

Crie um arquivo nesta pasta quando a revisão precisar de histórico, por exemplo:

- auditoria de documentação;
- revisão de arquitetura;
- revisão de cobertura, testes ou qualidade;
- checagem de aderência entre código e regras de agente.

## Formato sugerido

Nomeie arquivos com data e assunto, por exemplo:

- `20260602-auditoria-cursor-e-docs.md`
- `20260602-auditoria-architecture-boundaries.md`

Cada auditoria deve registrar:

- escopo revisado;
- achados principais;
- decisões tomadas;
- pendências ou riscos;
- arquivos e comandos usados na validação.

## Regra de manutenção

Auditorias são histórico, não fonte canônica de comportamento. Se um achado alterar entendimento durável do sistema, atualize a página temática correspondente em `docs/` e deixe a auditoria apenas como trilha de revisão.