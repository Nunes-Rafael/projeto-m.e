# Story 4: Testes end-to-end

## Status

Approved

## Módulo

Interface e entrega final

## Alocado a

Tanjiro

## Dependências

Stories 1 e 2 concluídas.

## Prioridade

Alta.

## Contexto completo

O fluxo verificável é: abrir chat, enviar pedido, receber resposta estruturada e observar requisição no histórico. O ambiente local usa adaptador determinístico; testes não usam OpenRouter nem DummyJSON reais. Falhas de validação e indisponibilidade devem preservar a experiência definida no documento de design.

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

## Evidências e pendências

- Verificado: página HTML é servida em `http://localhost:5173/`; build de produção do frontend conclui.
- Verificado: `docker compose exec -T backend python -m pytest -q` — 6 testes passam.
- Verificado: `docker compose exec -T mcp-server python -m pytest -q` — 6 testes passam.
- Pendente: teste de interação no browser e ação de nova tentativa no estado de indisponibilidade.
- O comando de build está documentado em `README.md`; os comandos das suítes existentes também.
