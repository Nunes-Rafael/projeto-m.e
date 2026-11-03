# Ciclo 04 — Diferenciais opcionais

## Status do ciclo

As quatro stories estão Done para o escopo da demonstração. A CI do GitHub passou no commit `9731db0` (jobs Python, frontend e configuration).

## Objetivo do ciclo

Acrescentar evidências de transparência, avaliação reproduzível e qualidade automatizada ao case, e então demonstrar a decisão de persistência via MCP com validações seguras.

| # | Story | Resultado | Dependências |
|---|---|---|---|
| 1 | [Exibir ferramentas chamadas](docs/stories/ciclo-04-diferenciais/01-ferramentas-no-chat.story.md) — Done | O chat mostra quais tools MCP foram usadas na requisição, incluindo `criar_requisicao` quando retornada. | Tanjiro aprovou correção; 4 testes UI + build, 2 backend unitários e 16 integrações DB isoladas passaram |
| 2 | [Script de avaliação com cinco pedidos](docs/stories/ciclo-04-diferenciais/02-script-avaliacao.story.md) — Done | Execução reproduzível e relatório de acertos por cenário. | QA Tanjiro aprovado; fixtures não medem seleção real do agente |
| 3 | [CI de lint e testes](docs/stories/ciclo-04-diferenciais/03-ci-lint-testes.story.md) — Done | Pipeline valida código e testes sem chamadas pagas. | Execução no GitHub aprovada: 3 jobs passaram |
| 4 | [Tool MCP para criar requisição](docs/stories/ciclo-04-diferenciais/04-tool-criar-requisicao.story.md) — Done | O agente solicita a persistência após a seleção; backend valida e MCP grava com atomicidade. | 20 testes MCP + 7 grants em banco descartável; QA Tanjiro aprovado; risco residual local documentado |

## Ordem e gates

As quatro stories estão Done para o escopo acordado. S2 usa fixtures determinísticas que não medem seleção real do agente. S4 foi aprovada para a demonstração local após testes isolados de autenticação, persistência, rollback, idempotência, grants e sanitização; a captura de logs cobriu nível INFO, não DEBUG do SDK MCP. O risco residual do role de escrita está documentado e o aceite não autoriza uso em produção. A CI remota passou nos três jobs no commit `9731db0`.

## Lacuna identificada ao conferir o PDF

O PDF descreve a avaliação como uma contagem de acertos do agente em cinco pedidos. A Story 2 entregue usa fixtures e mede regras determinísticas, sem chamar um LLM real. Isso mantém custo zero e repetibilidade, mas não comprova a qualidade do agente real. Extensão aprovada para planejamento no Ciclo 05: execução explícita e opt-in contra o modelo OpenAI configurado, com cinco pedidos, fixtures, critérios objetivos, custo/uso apresentado e sem execução na CI. Rafael autorizou teto de US$ 0,50 por execução. A arquitetura e a story estão em [`AVALIACAO-LLM-ARCH.md`](docs/architecture/AVALIACAO-LLM-ARCH.md) e [`01-avaliacao-agente-real.story.md`](docs/stories/ciclo-05-avaliacao-llm/01-avaliacao-agente-real.story.md); a implementação e a execução real permanecem pendentes.

## Gate de saída

- A interface identifica tools chamadas com dados reais da execução.
- O script de cinco cenários gera resultado legível e verifica conteúdo sem depender de igualdade textual do LLM.
- CI executa lint e testes sem segredos ou consumo de API.
- As quatro stories estão Done para a demonstração; os três jobs da CI remota passaram.
- Na Story 4, evidências devem comprovar fail-closed, grants efetivos, idempotência concorrente, rollback integral e sanitização. O risco residual da demonstração local permanece documentado e não autoriza uso em produção.
