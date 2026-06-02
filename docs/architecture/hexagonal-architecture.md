# Arquitetura Hexagonal

O Finance Manager segue uma arquitetura hexagonal explícita. A meta não é apenas organizar pastas: é manter a regra de negócio isolada de framework HTTP, ORM, banco, settings e detalhes de runtime.

## Direção de dependência

O fluxo conceitual continua sendo:

```text
Adapter/Input -> Port/Input -> UseCase -> Domain -> Port/Output -> Adapter/Output
```

Em termos de ownership:

- `src/core/domain/`: estruturas de negócio, enums e erros de domínio.
- `src/core/ports/`: contratos de entrada e saída possuídos pelo core.
- `src/core/usecases/`: orquestração, fronteiras transacionais e invariantes cruzando agregados.
- `src/adapters/input/`: tradução HTTP -> core e core -> HTTP.
- `src/infra/`: implementações concretas, bootstrap, runtime, banco, logging e settings.

## Limites protegidos por teste

A referência executável é `tests/architecture/test_boundaries.py`. As regras mais importantes hoje são:

- `core` não importa `adapters` nem `infra`.
- `core.domain` não importa `ports`, `usecases`, `adapters` ou `infra`.
- `ports` não importam `usecases`, `adapters` ou `infra`.
- `usecases` não importam `adapters` nem `infra`.
- `adapters` não importam `infra`.
- `adapters.input` não importam `core.usecases`.
- `adapters.output` não importam `core.usecases` nem `adapters.input`.
- `infra.settings` e `infra.logging` não importam `adapters`.
- `infra.bootstrap`, `infra.main` e `infra.postgres` não importam `adapters`.
- `infra.fastapi` não importa `adapters.output`.
- `core.shared` não importa `adapters` nem `infra`.

Quando uma mudança parece pedir violação desses limites, trate isso como decisão arquitetural explícita. Não normalize imports ilegais “só para resolver rápido”.

## Composition root e runtime

O composition root principal está em `src/infra/bootstrap.py`.

Hoje ele:

- carrega settings;
- cria engine e session factory do Postgres;
- instancia adapters concretos, como health e exchange rate;
- instancia os use cases e injeta suas dependências via ports.

O app HTTP é montado em `src/infra/fastapi/app.py`, que recebe settings e input ports prontos e apenas compõe o runtime FastAPI. O comando de desenvolvimento sobe `src.infra.main:create_app` via Uvicorn, preservando a separação entre bootstrap, app factory e entrypoint.

## Settings e logging

Os settings continuam pertencendo à infra. A referência canônica é `src/infra/settings/models.py`, e o carregamento é centralizado no bootstrap.

Consequências práticas:

- defaults operacionais não devem ser espalhados por rotas, use cases ou helpers soltos;
- comportamento de ambiente, FastAPI, Postgres e logging deve nascer dos settings;
- logging é configurado em `src/infra/logging/` e acionado na criação do app FastAPI, não de forma ad-hoc em múltiplos pontos.

## Security e hashing

Hash de senha é exposto ao core por port e implementado concretamente na infra.

O padrão atual é:

- implementação concreta: `ScryptPasswordHasher`;
- formato persistido: `scrypt$n=16384$r=8$p=1$dklen=64$salt$hash`;
- o formato legado `scrypt$salt$hash` não é suportado.

Esse detalhe não pertence ao `README.md`, mas também não deve desaparecer da documentação técnica, porque afeta evolução de autenticação, migração e compatibilidade.

## Consequências práticas

- Regras de negócio não moram em rota HTTP.
- Repositórios não definem a transação; o use case define, por meio do Unit of Work.
- Se um novo aggregate precisar participar da mesma transação, o contrato do Unit of Work e o wiring de bootstrap precisam evoluir juntos.
- `src/core/shared/` deve continuar pequeno. Se um helper tiver semântica de domínio, ele não pertence a `shared/` só porque foi reutilizado duas vezes.

## Arquivos canônicos

- `tests/architecture/test_boundaries.py`
- `src/infra/bootstrap.py`
- `src/infra/fastapi/app.py`
- `src/infra/settings/models.py`
- `src/infra/logging/`
- `src/infra/security/`
- `Makefile`