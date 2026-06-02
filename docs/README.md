# Documentação Técnica

Esta pasta concentra a documentação técnica canônica e de longa duração do repositório. Cada assunto deve ter um ponto canônico de explicação; nos outros lugares, prefira só apontadores curtos.

## Camadas

- `README.md`: visão pública, curta e orientada a apresentação do projeto. Não deve carregar regras internas de implementação, instruções permanentes para IA ou convenções operacionais detalhadas.
- `.cursor/rules/`: regras permanentes, curtas, acionáveis e reutilizáveis pelo Cursor. Devem orientar comportamento, não substituir documentação longa.
- `docs/`: conhecimento técnico canônico e de longa duração. Aqui ficam racional, contexto, arquitetura, persistência, API, testes, operação e decisões duráveis.

## Ordem de consulta recomendada

1. código e testes atuais
2. `Makefile`, `pyproject.toml` e settings reais
3. `docs/`
4. `README.md`

## Começo rápido

Se o objetivo for começar desenvolvimento com contexto forte, a sequência mínima recomendada é:

1. `meta/project-context.md`
2. `meta/current-state.md`
3. `architecture/hexagonal-architecture.md`
4. `architecture/code-patterns-and-preferences.md`
5. `domain/product-decisions.md`
6. `domain/transactions.md` quando a mudança tocar fluxo monetário ou lifecycle de transaction
7. a página temática específica da área alterada (`api/`, `persistence/`, `testing/` ou `operations/`)

## Mapa inicial

- `meta/`: ponto de entrada curto para agentes, snapshots do estado atual e metadocumentação de contexto.
- `architecture/`: limites hexagonais, responsabilidades de camada, composition root, runtime e padrões de código.
- `domain/`: modelo do produto, invariantes, semântica dos agregados e decisões de negócio.
- `api/`: convenções HTTP, mapeamento de erro, paginação e contratos públicos.
- `persistence/`: organização Postgres, Unit of Work, repositórios e migrations.
- `testing/`: estrutura da suíte, reutilização de helpers e barra de qualidade.
- `operations/`: setup local, comandos, runtime e fluxo de validação.
- `audits/`: snapshots datados de revisões; não substituem a documentação canônica.
- `adr/`: decisões arquiteturais duráveis registradas separadamente.

## Regra de manutenção

Quando uma mudança tocar arquitetura, contrato público, convenção de teste, estratégia de persistência ou fluxo operacional, atualize a página temática correspondente nesta pasta na mesma entrega.

Se a mudança alterar o panorama do repositório para agentes ou o escopo efetivo do MVP, atualize também `meta/project-context.md` ou `meta/current-state.md`, conforme o caso.

Se a mudança for apenas uma orientação operacional curta e permanente para o Cursor, coloque isso em `.cursor/rules/`. Se a mudança exigir explicação, contexto, exceções, racional ou exemplos, ela pertence a `docs/`.

Evite duplicação entre camadas: mantenha a explicação completa em um lugar só e use referências curtas nos demais.