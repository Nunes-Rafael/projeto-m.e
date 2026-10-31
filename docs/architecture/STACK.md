# STACK — Agente de Compras MCP

## Decisões registradas

| Decisão | Escolha | Justificativa e trade-off |
|---|---|---|
| Estrutura | Monorepo com `backend/`, `mcp-server/`, `frontend/` e `compose.yaml` | Mantém os quatro componentes do case visíveis e isolados, sem custo de múltiplos repositórios. |
| Frontend | React + Vite | É o suficiente para o chat pedido; evita a complexidade de SSR para uma única tela interna. |
| Backend | Python + FastAPI | Contratos HTTP tipados, validação de payload e boa integração com cliente MCP e SDK de LLM. |
| Servidor de ferramentas | Python + SDK MCP, transporte HTTP | Expõe as duas ferramentas como um serviço independente e testável sem LLM. |
| Catálogo | DummyJSON, acessado somente pelo servidor MCP | O backend não chama o catálogo diretamente; preserva a fronteira MCP exigida no case. |
| Persistência | PostgreSQL em container | O case exige Postgres e relações estruturadas entre requisição e itens. |
| API do produto | REST sob `/requisicoes` | Há somente um cliente e dois recursos simples; GraphQL ou RPC adicionariam complexidade sem benefício. |
| Inicialização | Docker Compose + healthchecks + migrações idempotentes do backend | O avaliador inicia tudo com um comando e não prepara banco manualmente. |
| LLM em produção do case | Adaptador OpenRouter, habilitado apenas com `OPENROUTER_API_KEY` | Atende ao fluxo de tool-calling quando existir credencial. A chave nunca é gravada, exibida ou logada. |
| Desenvolvimento sem chave | Modo local explícito e determinístico | Permite desenvolver UI, MCP, banco e falhas. Não substitui a validação do requisito de o LLM decidir chamadas de ferramenta. |

## Topologia local

```text
Browser
  │ HTTP
  ▼
frontend (React) ──HTTP──> backend (FastAPI) ──MCP/HTTP──> mcp-server ──HTTP──> DummyJSON
                                  │
                                  └────────SQL──────────> postgres
```

O `frontend` nunca conhece a chave do provedor de LLM, credenciais de banco ou URL externa do catálogo. O `backend` é o único processo que conversa com o cliente MCP e que grava no Postgres.

## Variáveis e segredos

| Variável | Dono | Regra |
|---|---|---|
| `DATABASE_URL` | backend | Define conexão interna com Postgres; não é enviada ao frontend. |
| `MCP_SERVER_URL` | backend | URL interna do servidor MCP no Compose. |
| `AGENT_MODE` | backend | `local` por padrão; `openrouter` somente com chave válida. |
| `OPENROUTER_API_KEY` | backend | Opcional no desenvolvimento, nunca versionada ou logada. |
| `OPENROUTER_MODEL` | backend | Nome do modelo com suporte a tool-calling; obrigatório no modo `openrouter`. |

`.env` é ignorado pelo Git. Apenas `.env.example`, sem valores secretos, pode ser versionado.

## Decisões deliberadamente adiadas

- Sem autenticação, filas, cache, n8n, Supabase ou ERP no MVP.
- Sem persistir conversas, prompts completos ou conteúdo de credenciais.
- A terceira ferramenta MCP para salvar requisição só será considerada após o fluxo obrigatório passar nos testes.

