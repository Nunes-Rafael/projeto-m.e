# Ciclo 04 — Diferenciais opcionais

## Status do ciclo

Stories 1, 2 e 4 estão Done para o escopo da demonstração local. Story 3 está em Review: as verificações passaram localmente, mas o workflow ainda não foi executado no GitHub.

## Objetivo do ciclo

Acrescentar evidências de transparência, avaliação reproduzível e qualidade automatizada ao case, e então demonstrar a decisão de persistência via MCP com validações seguras.

| # | Story | Resultado | Dependências |
|---|---|---|---|
| 1 | [Exibir ferramentas chamadas](docs/stories/ciclo-04-diferenciais/01-ferramentas-no-chat.story.md) — Done | O chat mostra quais tools MCP foram usadas na requisição, incluindo `criar_requisicao` quando retornada. | Tanjiro aprovou correção; 4 testes UI + build, 2 backend unitários e 16 integrações DB isoladas passaram |
| 2 | [Script de avaliação com cinco pedidos](docs/stories/ciclo-04-diferenciais/02-script-avaliacao.story.md) — Done | Execução reproduzível e relatório de acertos por cenário. | QA Tanjiro aprovado; fixtures não medem seleção real do agente |
| 3 | [CI de lint e testes](docs/stories/ciclo-04-diferenciais/03-ci-lint-testes.story.md) — Review | Pipeline valida código e testes sem chamadas pagas. | Comandos verificados localmente; execução no GitHub pendente |
| 4 | [Tool MCP para criar requisição](docs/stories/ciclo-04-diferenciais/04-tool-criar-requisicao.story.md) — Done | O agente solicita a persistência após a seleção; backend valida e MCP grava com atomicidade. | 20 testes MCP + 7 grants em banco descartável; QA Tanjiro aprovado; risco residual local documentado |

## Ordem e gates

S1, S2 e S4 estão Done após QA. S2 usa fixtures determinísticas que não medem seleção real do agente. S4 foi aprovada para a demonstração local após testes isolados de autenticação, persistência, rollback, idempotência, grants e sanitização; a captura de logs cobriu nível INFO, não DEBUG do SDK MCP. O risco residual do role de escrita está documentado e o aceite não autoriza uso em produção. A Story 3 foi validada localmente, mas permanece em Review até uma execução externa do workflow no GitHub.

## Gate de saída

- A interface identifica tools chamadas com dados reais da execução.
- O script de cinco cenários gera resultado legível e verifica conteúdo sem depender de igualdade textual do LLM.
- CI executa lint e testes sem segredos ou consumo de API.
- Stories 1, 2 e 4 estão Done para a demonstração local.
- Story 3 permanece em Review até a execução do workflow no GitHub.
- Na Story 4, evidências devem comprovar fail-closed, grants efetivos, idempotência concorrente, rollback integral e sanitização. O risco residual da demonstração local permanece documentado e não autoriza uso em produção.
