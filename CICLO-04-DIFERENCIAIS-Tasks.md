# Ciclo 04 — Diferenciais opcionais

## Status do ciclo

As quatro stories estão Done para o escopo da demonstração. A CI do GitHub passou nos commits `9731db0` e `849c009` (jobs Python, frontend e configuration).

## Objetivo do ciclo

Acrescentar evidências de transparência, avaliação reproduzível e qualidade automatizada ao case, e então demonstrar a decisão de persistência via MCP com validações seguras.

| # | Story | Resultado | Dependências |
|---|---|---|---|
| 1 | [Exibir ferramentas chamadas](docs/stories/ciclo-04-diferenciais/01-ferramentas-no-chat.story.md) — Done | O chat mostra quais tools MCP foram usadas na requisição, incluindo `criar_requisicao` quando retornada. | Tanjiro aprovou correção; 4 testes UI + build, 2 backend unitários e 16 integrações DB isoladas passaram |
| 2 | [Script de avaliação com cinco pedidos](docs/stories/ciclo-04-diferenciais/02-script-avaliacao.story.md) — Done | Execução reproduzível e relatório de acertos por cenário. | QA Tanjiro aprovado; fixtures não medem seleção real do agente |
| 3 | [CI de lint e testes](docs/stories/ciclo-04-diferenciais/03-ci-lint-testes.story.md) — Done | Pipeline valida código e testes sem chamadas pagas. | Execução no GitHub aprovada: 3 jobs passaram |
| 4 | [Tool MCP para criar requisição](docs/stories/ciclo-04-diferenciais/04-tool-criar-requisicao.story.md) — Done | O agente solicita a persistência após a seleção; backend valida e MCP grava com atomicidade. | 20 testes MCP + 7 grants em banco descartável; QA Tanjiro aprovado; risco residual local documentado |

## Ordem e gates

As quatro stories estão Done para o escopo acordado. S2 usa fixtures determinísticas que não medem seleção real do agente; essa lacuna foi complementada pela Story do Ciclo 05. S4 foi aprovada para a demonstração local após testes isolados de autenticação, persistência, rollback, idempotência, grants e sanitização; a captura de logs cobriu nível INFO, não DEBUG do SDK MCP. O risco residual do role de escrita está documentado e o aceite não autoriza uso em produção. A CI remota passou nos três jobs nos commits `9731db0` e `849c009`.

## Extensão entregue no Ciclo 05

A Story 2 continua oferecendo avaliação determinística com fixtures, sem custo e com resultado reproduzível. A lacuna de não executar o agente real foi atendida no Ciclo 05: uma avaliação opt-in usou o modelo configurado, cinco pedidos sintéticos, catálogo e persistência em memória e critérios objetivos. A execução autorizada passou em 5/5 cenários e reportou uso e custo estimado, sem acessar PostgreSQL, MCP ou DummyJSON. O teto de US$ 0,50 limita a reserva estimada pelo programa, não garante a cobrança final do provedor. Consulte [`AVALIACAO-LLM-ARCH.md`](docs/architecture/AVALIACAO-LLM-ARCH.md) e [`01-avaliacao-agente-real.story.md`](docs/stories/ciclo-05-avaliacao-llm/01-avaliacao-agente-real.story.md).

## Gate de saída

- A interface identifica tools chamadas com dados reais da execução.
- O script de cinco cenários gera resultado legível e verifica conteúdo sem depender de igualdade textual do LLM.
- CI executa lint e testes sem segredos ou consumo de API.
- As quatro stories estão Done para a demonstração; os três jobs da CI remota passaram.
- Na Story 4, evidências devem comprovar fail-closed, grants efetivos, idempotência concorrente, rollback integral e sanitização. O risco residual da demonstração local permanece documentado e não autoriza uso em produção.
