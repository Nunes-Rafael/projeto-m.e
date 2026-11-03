# Story 4: Testes end-to-end

## Status

Review — fluxo manual de sucesso e integração entre serviços validados; automação de browser, erros e retry ainda pendentes.

## Módulo

Interface e entrega final

## Alocado a

Tanjiro

## Dependências

Stories 1 e 2 concluídas.

## Prioridade

Alta.

## Contexto completo

O fluxo verificável é: abrir chat, enviar pedido, receber resposta estruturada e observar requisição no histórico. Testes automatizados usam fixtures determinísticas, sem chamadas pagas nem dependência do catálogo externo. A demonstração manual em modo OpenAI valida a interpretação do pedido pelo modelo e a chamada das ferramentas MCP. Falhas de validação e indisponibilidade devem preservar a experiência definida no documento de design.

## O que fazer

Criar testes de ponta a ponta ou de fronteira equivalente para sucesso, erro de validação, incompatibilidade e falha temporária. Validar a apresentação de número, itens e total no fluxo bem-sucedido.

## Critérios de aceite

- [ ] Fluxo bem-sucedido cobre envio, resposta e atualização de histórico.
- [ ] Erro de validação mantém o pedido editável.
- [ ] Indisponibilidade apresenta ação de nova tentativa sem expor detalhes internos.
- [ ] Testes não exigem rede externa, chave ou intervenção manual.
- [ ] Comando de execução integra a documentação.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-10-31 | Review | `docker compose up --build -d` subiu os quatro serviços; Vite serviu a página e `npm run build` passou. Backend e MCP passaram cada um 6 testes, sem chave de LLM. Não há runner de browser instalado, então não foi possível automatizar a interação real no navegador. Revisão visual do fluxo encontrou um desvio do aceite: erro temporário oferece “Editar pedido”, mas ainda não oferece a ação “Tentar novamente”. |
| 2026-11-02 | Review | Fluxo de serviços em Compose descartável validado: página do frontend servida, backend acessado, catálogo consultado, tools MCP executadas e requisição persistida/listada no PostgreSQL exclusivo. O teste passou pela API do backend; o proxy HTTP temporário do Vite não foi concluído e não houve interação automatizada em navegador. Retry de erro temporário também continua pendente. |
| 2026-11-02 | Review | Rafael validou manualmente no navegador o fluxo com `AGENT_MODE=openai`: pedido de 3 laptops, limite de US$ 2.000 por unidade, resposta `#0002`, ferramentas `buscar_produtos`, `detalhar_produto` e `criar_requisicao`, e atualização da lista recente. Consulta read-only ao PostgreSQL confirmou três linhas, uma unidade por produto, preços unitários abaixo do teto e total de US$ 5.199,97 igual à soma dos itens. O teste usou LLM real e gravou no banco local; não é uma execução automatizada. Erros de validação, indisponibilidade e retry continuam sem evidência de browser. |

## Evidências e pendências

- Verificado: página HTML é servida em `http://localhost:5173/`; build de produção do frontend conclui.
- Verificado: `docker compose exec -T backend python -m pytest -q` — 6 testes passam.
- Verificado: `docker compose exec -T mcp-server python -m pytest -q` — 6 testes passam.
- Verificado manualmente: fluxo de sucesso no browser com LLM, MCP e gravação/listagem confirmada no PostgreSQL.
- Pendente: automação de browser; validação visual/funcional dos erros; ação de nova tentativa no estado de indisponibilidade.
- O comando de build está documentado em `README.md`; os comandos das suítes existentes também.
