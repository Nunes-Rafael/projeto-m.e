# Story 1: Schema Postgres e migração idempotente

## Status

Review

## Módulo

Backend, persistência e agente

## Alocado a

Jin-Woo

## Dependências

Nenhuma.

## Prioridade

Crítica.

## Contexto completo

Uma requisição possui UUID, número sequencial único, pedido original, status `criada`, valor total decimal e data. Cada item é snapshot do catálogo com produto de origem, título, quantidade, preço unitário e total decimal. Não existem estados parciais. O schema deve ser criado automaticamente na subida do ambiente.

## O que fazer

Implementar schema, índices e migração/initialization idempotente para Postgres. Usar decimal exato para valores monetários e garantir transações possíveis no repositório do backend.

## Critérios de aceite

- [ ] `requisicoes` e `itens_requisicao` possuem os campos e relações definidos na arquitetura.
- [ ] Número da requisição é único; itens possuem índice por requisição; listagem possui índice de criação.
- [ ] Valores monetários não usam `float` binário.
- [ ] Nova subida do ambiente não falha se o schema já existir.
- [ ] Banco vazio pode responder a listagem sem preparação manual.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-10-31 | Draft | Story criada para tornar a persistência verificável e idempotente. |
| 2026-10-31 | Review | Criadas tabelas normalizadas com valores `NUMERIC`, restrições, índices e inicialização idempotente no ciclo de vida do FastAPI, para o banco estar pronto antes da API aceitar tráfego. |
