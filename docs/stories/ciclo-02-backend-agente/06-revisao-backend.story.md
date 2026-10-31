# Story 6: Revisão de API e segurança

## Status

Done

## Módulo

Backend, persistência e agente

## Alocado a

Near e Gojo

## Dependências

Stories 1 a 5 concluídas.

## Prioridade

Alta.

## Contexto completo

O backend recebe texto livre, acessa somente MCP, persiste compra e possui modo opcional de LLM externo. Não há autenticação ou dados pessoais no MVP, mas erros, parâmetros e segredos precisam ser protegidos.

## O que fazer

Revisar limites de domínio, validação, transações, tratamento de erros e configuração de segredos. Classificar achados e liberar o ciclo somente sem falhas críticas.

## Critérios de aceite

- [x] Não há chamadas diretas à DummyJSON pelo backend.
- [x] Chaves e prompts completos não aparecem em logs/respostas.
- [x] Entrada, tools e resposta final possuem validação explícita.
- [x] Falhas de transação não deixam itens órfãos ou cabeçalhos parciais.
- [x] Não há achado crítico pendente.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-10-31 | Draft | Story criada como gate de qualidade para a primeira API persistente do projeto. |
| 2026-10-31 | Review | Testes de integração passam e o backend acessa o catálogo apenas via MCP, mas o ciclo não recebe sign-off: a validação final aceita qualquer `detalhar_produto` retornado pelo MCP sem provar que o produto veio de uma busca desta execução. Isso viola o contrato arquitetural de origem no catálogo. Também falta distinguir `no_compatible_product` de `agent_result_invalid`, e argumentos JSON inválidos retornados pelo provedor no modo OpenRouter podem escapar como erro interno. |
| 2026-10-31 | Review | Revisão de segurança: não há chamada direta ao catálogo pelo backend; o cliente MCP mantém allowlist e valida argumentos; chaves e o PDF não estão rastreados, e erros públicos não incluem detalhes de transporte. Sem achado crítico adicional para o escopo local. Antes de qualquer exposição pública, adicionar autenticação e limitação de taxa. O sign-off final permanece pendente das correções de integridade e tratamento de erro identificadas na revisão de qualidade. |
| 2026-10-31 | Review | Correções aplicadas: a execução registra IDs retornados por busca e só detalha itens com essa origem; ausência de compatibilidade retorna código público distinto; JSON inválido em tool-calling externo é convertido em `AgentError`. Seis testes de integração passam, incluindo origem inválida e ausência de compatibilidade. |
| 2026-10-31 | Done | Sign-off de qualidade após `cf23583`: os três bloqueios foram resolvidos. A proveniência é controlada por execução, a ausência de produto usa código público próprio e JSON inválido em tool-calling vira erro de domínio. Seis testes passam; nenhum bloqueio crítico permanece. |
