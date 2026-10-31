# Story 5: Testes de integração do backend

## Status

Approved

## Módulo

Backend, persistência e agente

## Alocado a

Tanjiro

## Dependências

Story 4 concluída.

## Prioridade

Crítica.

## Contexto completo

Os testes devem validar comportamento externo do backend com cliente MCP e adaptador de agente substituíveis. Não podem chamar OpenRouter ou DummyJSON reais. A persistência precisa ser verificada em banco de teste ou container dedicado.

## O que fazer

Cobrir sucesso, nenhum produto compatível, timeout/falha de catálogo, saída inválida do agente, configuração ausente do OpenRouter e listagem de requisições.

## Critérios de aceite

- [ ] Teste de POST bem-sucedido valida resposta e persistência.
- [ ] Teste de GET valida ordenação e resumo da requisição.
- [ ] Casos sem produto e de falha externa confirmam ausência de persistência parcial.
- [ ] Nenhum teste requer segredo ou rede externa.
- [ ] Comando único de teste é reproduzível no container/backend.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-10-31 | Draft | Story criada para verificar o contrato HTTP e as garantias de transação. |
