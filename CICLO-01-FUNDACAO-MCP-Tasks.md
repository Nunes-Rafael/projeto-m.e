# Ciclo 01 — Fundação e MCP

## Objetivo do ciclo

Deixar o ambiente reproduzível e o catálogo acessível exclusivamente por duas ferramentas MCP, com testes independentes de LLM.

| # | Story | Responsável | Status | Dependências |
|---|---|---|---|---|
| 1 | [Fundação do ambiente](docs/stories/ciclo-01-fundacao-mcp/01-fundacao.story.md) | Itachi | Approved | Nenhuma |
| 2 | [Servidor MCP e ferramentas de catálogo](docs/stories/ciclo-01-fundacao-mcp/02-servidor-mcp.story.md) | Gohan | Approved | Story 1 |
| 3 | [Testes independentes do MCP](docs/stories/ciclo-01-fundacao-mcp/03-testes-mcp.story.md) | Tanjiro | Approved | Story 2 |
| 4 | [Revisão de integração e segredos](docs/stories/ciclo-01-fundacao-mcp/04-revisao-fundacao.story.md) | Near e Gojo | Approved | Stories 1–3 |

## Gate de saída

- `docker compose up --build` inicia frontend, backend, servidor MCP e Postgres sem preparação manual.
- As duas ferramentas MCP possuem testes sem chave de LLM e sem acesso real à DummyJSON.
- Nenhum segredo ou material do case é rastreado pelo Git.
