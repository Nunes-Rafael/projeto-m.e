# Ciclo 04 — Diferenciais opcionais

## Status do ciclo

Proposta em Draft. As quatro stories permanecem em Draft até Rafael aprovar o ciclo. A revisão técnica da Story 4 pode produzir a especificação, mas não autoriza sua implementação.

## Objetivo do ciclo

Acrescentar evidências de transparência, avaliação reproduzível e qualidade automatizada ao case, e então demonstrar a decisão de persistência via MCP com validações seguras.

| # | Story | Resultado | Dependências |
|---|---|---|---|
| 1 | [Exibir ferramentas chamadas](docs/stories/ciclo-04-diferenciais/01-ferramentas-no-chat.story.md) | O chat mostra quais tools MCP foram usadas na requisição. | Ciclo 03 concluído |
| 2 | [Script de avaliação com cinco pedidos](docs/stories/ciclo-04-diferenciais/02-script-avaliacao.story.md) | Execução reproduzível e relatório de acertos por cenário. | Ciclo 03 concluído; API e modo local |
| 3 | [CI de lint e testes](docs/stories/ciclo-04-diferenciais/03-ci-lint-testes.story.md) | Pipeline valida código e testes sem chamadas pagas. | Stories 1 e 2 |
| 4 | [Tool MCP para criar requisição](docs/stories/ciclo-04-diferenciais/04-tool-criar-requisicao.story.md) | O agente pode solicitar a persistência após a seleção; backend valida e mantém atomicidade. | Ciclo 03 concluído; especificação de Senku em `docs/architecture/OPCIONAIS-ARCH.md` revisada e aprovada por Rafael antes de implementar |

## Ordem e gates

As Stories 1 e 2 podem ser desenvolvidas independentemente após o Ciclo 03. A Story 3 depende dos comandos e verificações definidos nas Stories 1 e 2. A Story 4 é independente dessas entregas: Senku documenta a arquitetura em `docs/architecture/OPCIONAIS-ARCH.md`; Rafael revisa e aprova essa especificação e o escopo da story antes de qualquer implementação. A revisão de segurança é um gate de conclusão da Story 4.

## Gate de saída

- A interface identifica tools chamadas com dados reais da execução.
- O script de cinco cenários gera resultado legível e verifica conteúdo sem depender de igualdade textual do LLM.
- CI executa lint e testes sem segredos ou consumo de API.
- As quatro stories continuam Draft até a aprovação de Rafael.
- A Story 4 não começa a ser implementada sem `docs/architecture/OPCIONAIS-ARCH.md` revisado e aprovado por Rafael; nenhum pedido incompatível ou não validado pode ser persistido.
