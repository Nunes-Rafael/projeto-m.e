# Ciclo 04 — Diferenciais opcionais

## Objetivo do ciclo

Acrescentar evidências de transparência, avaliação reproduzível e qualidade automatizada ao case, e então demonstrar a decisão de persistência via MCP com validações seguras.

| # | Story | Resultado | Dependências |
|---|---|---|---|
| 1 | [Exibir ferramentas chamadas](docs/stories/ciclo-04-diferenciais/01-ferramentas-no-chat.story.md) | O chat mostra quais tools MCP foram usadas na requisição. | Ciclo 03 concluído |
| 2 | [Script de avaliação com cinco pedidos](docs/stories/ciclo-04-diferenciais/02-script-avaliacao.story.md) | Execução reproduzível e relatório de acertos por cenário. | Story 1; API e modo local |
| 3 | [CI de lint e testes](docs/stories/ciclo-04-diferenciais/03-ci-lint-testes.story.md) | Pipeline valida código e testes sem chamadas pagas. | Stories 1 e 2 |
| 4 | [Tool MCP para criar requisição](docs/stories/ciclo-04-diferenciais/04-tool-criar-requisicao.story.md) | O agente pode solicitar a persistência após a seleção; backend valida e mantém atomicidade. | Stories 1–3; revisão arquitetural antes de implementar |

## Ordem e gates

As Stories 1–3 são diferenciais de baixo risco e podem ser entregues em sequência. A Story 4 altera a fronteira de persistência e só começa depois da aprovação de sua especificação técnica e dos cenários de segurança.

## Gate de saída

- A interface identifica tools chamadas com dados reais da execução.
- O script de cinco cenários gera resultado legível e verifica conteúdo sem depender de igualdade textual do LLM.
- CI executa lint e testes sem segredos ou consumo de API.
- Se a Story 4 for aprovada e implementada, nenhum pedido incompatível ou não validado pode ser persistido.
