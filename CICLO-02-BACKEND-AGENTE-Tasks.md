# Ciclo 02 — Backend, persistência e agente

## Objetivo do ciclo

Entregar uma API persistente de requisições que consulta o catálogo somente via MCP e funciona em modo local, mantendo o adaptador OpenRouter configurável sem segredos.

| # | Story | Responsável | Status | Dependências |
|---|---|---|---|---|
| 1 | [Schema e migração idempotente](docs/stories/ciclo-02-backend-agente/01-schema-postgres.story.md) | Jin-Woo | Approved | Nenhuma |
| 2 | [Cliente MCP e contratos internos](docs/stories/ciclo-02-backend-agente/02-cliente-mcp.story.md) | Gohan | Approved | Ciclo 01 concluído |
| 3 | [Adaptadores do agente](docs/stories/ciclo-02-backend-agente/03-adaptadores-agente.story.md) | Gohan | Approved | Story 2 |
| 4 | [API e transação de requisição](docs/stories/ciclo-02-backend-agente/04-api-requisicoes.story.md) | Gohan | Approved | Stories 1–3 |
| 5 | [Testes de integração](docs/stories/ciclo-02-backend-agente/05-testes-integracao.story.md) | Tanjiro | Approved | Story 4 |
| 6 | [Revisão de API e segurança](docs/stories/ciclo-02-backend-agente/06-revisao-backend.story.md) | Near e Gojo | Approved | Stories 1–5 |

## Gate de saída

- `POST /requisicoes` persiste uma resposta válida e `GET /requisicoes` a lista.
- O backend não acessa DummyJSON diretamente.
- Casos sem compatibilidade, timeout e saída inválida não persistem linhas parciais.
- Os testes de integração não exigem chave de LLM.
