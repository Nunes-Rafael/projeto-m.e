# Story 6: Revisão de API e segurança

## Status

Approved

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

- [ ] Não há chamadas diretas à DummyJSON pelo backend.
- [ ] Chaves e prompts completos não aparecem em logs/respostas.
- [ ] Entrada, tools e resposta final possuem validação explícita.
- [ ] Falhas de transação não deixam itens órfãos ou cabeçalhos parciais.
- [ ] Não há achado crítico pendente.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-10-31 | Draft | Story criada como gate de qualidade para a primeira API persistente do projeto. |
