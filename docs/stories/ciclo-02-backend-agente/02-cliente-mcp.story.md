# Story 2: Cliente MCP e contratos internos

## Status

Approved

## Módulo

Backend, persistência e agente

## Alocado a

Gohan

## Dependências

Ciclo 01 concluído.

## Prioridade

Crítica.

## Contexto completo

O backend não chama DummyJSON diretamente. Ele conversa com o servidor MCP já entregue e só pode invocar `buscar_produtos` e `detalhar_produto`. Chamadas aceitam schemas conhecidos, têm timeout e erros seguros.

## O que fazer

Implementar cliente MCP no backend, descoberta/registro explícito das duas tools e mapeamento de erros do MCP para erros internos estáveis.

## Critérios de aceite

- [ ] Backend não contém cliente HTTP para DummyJSON.
- [ ] Apenas as duas tools registradas podem ser chamadas.
- [ ] Argumentos são validados antes do envio ao MCP.
- [ ] Falha de protocolo, timeout ou tool indisponível gera erro interno seguro.
- [ ] O cliente pode ser substituído por fake nos testes.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-10-31 | Draft | Story criada para preservar a fronteira MCP entre agente e catálogo. |
