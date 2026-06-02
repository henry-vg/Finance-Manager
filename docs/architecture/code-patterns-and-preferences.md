# Padrões de Código e Preferências

Esta página é a referência canônica para padrões de implementação, nomenclatura e preferências técnicas do repositório. As rules do Cursor devem resumir essas diretrizes, não reexplicá-las.

## Objetivo

O projeto prefere código explícito, previsível e fácil de auditar. A meta não é “engenhosidade”, e sim legibilidade estrutural dentro da arquitetura hexagonal.

## Nomenclatura canônica

Use nomes que deixem o papel arquitetural claro.

- DTOs de entrada do domínio: `Create*Data` e `Update*Data`
- Objetos finais antes de persistir ou enviar a output ports: `New*` e `*Changes`
- Casos de uso: `*UseCase`
- Contratos do core: `*InputPort` e `*OutputPort`
- Exceções: `*Error`
- Modelos SQLAlchemy: `*Record`
- Doubles de teste fixos: `*Stub`

Exemplos atuais:

- `TransactionInputPort`
- `TransactionUseCase`
- `UserRecord`
- `TransactionInputPortStub`
- `TransactionNotFoundError`

## Preferências de implementação

- Prefira a menor mudança que corrige a causa real no ponto que possui a responsabilidade.
- Mantenha mapeamentos importantes explícitos.
- Não esconda regra de negócio relevante atrás de helpers opacos.
- Não extraia abstração compartilhada só porque apareceu a primeira duplicação.
- Quando houver helpers privados em classes, prefira mantê-los perto do `__init__` e antes da API pública da classe.

## Tipos e modelagem

- Use `dataclass` para portadores internos simples.
- Use Pydantic quando parsing, validação ou serialização forem parte real da responsabilidade.
- `Decimal` é a escolha correta para valores monetários; não use `float`.
- Enums fechados do core permanecem no domínio; enums públicos de contrato HTTP permanecem nos schemas/adapters.

## Padrões por camada

### Core

- `domain/` contém estruturas de negócio, enums e erros agnósticos de tecnologia.
- `usecases/` orquestram fluxo, transação e invariantes cruzando agregados.
- `shared/` fica pequeno, estável e realmente transversal.

### Adapters HTTP

- handlers são finos;
- fazem parsing, chamam input ports e mapeiam resposta/erro;
- não carregam regra de negócio do produto.

### Persistência

- repositórios são session-bound;
- podem usar `flush()` e `refresh()`;
- não fazem `commit()` nem `rollback()`;
- a transação pertence ao use case via Unit of Work.

### Testes

- prefira nomes comportamentais;
- reutilize builders e stubs compartilhados quando a superfície já tiver helpers canônicos;
- não crie doubles locais redundantes sem necessidade real.

## Estratégia de leitura para o Cursor

Ao tocar uma área nova:

1. leia a rule curta correspondente em `.cursor/rules/`;
2. leia a página temática de `docs/`;
3. confirme o padrão no código canônico daquela camada.

## Arquivos canônicos

- `docs/architecture/hexagonal-architecture.md`
- `src/core/`
- `src/adapters/input/api/`
- `src/infra/postgres/`
- `tests/integration/fastapi/helpers/stubs.py`