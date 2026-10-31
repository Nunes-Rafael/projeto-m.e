# Story 4: API, validação e transação de requisição

## Status

Approved

## Módulo

Backend, persistência e agente

## Alocado a

Gohan

## Dependências

Stories 1, 2 e 3 concluídas.

## Prioridade

Crítica.

## Contexto completo

`POST /requisicoes` recebe pedido de até 2.000 caracteres e retorna `201` apenas após validar itens contra os dados de catálogo da própria execução, recalcular totais decimais e gravar cabeçalho e itens na mesma transação. `GET /requisicoes` ordena por criação decrescente. Erros públicos usam envelope estável `erro.codigo` e `erro.mensagem`.

## O que fazer

Implementar os endpoints, orquestração do agente, validação de teto por unidade, persistência transacional e mapeamento de erros conforme arquitetura.

## Critérios de aceite

- [ ] Pedido válido retorna `201` com número, itens, valores e justificativa.
- [ ] `GET /requisicoes` encontra a requisição recém-criada.
- [ ] Pedido vazio/longa demais retorna `422 invalid_request`.
- [ ] Sem produto compatível, saída inválida ou erro de catálogo não deixam dados parciais.
- [ ] Indisponibilidade de catálogo retorna `503 catalog_unavailable`; agente indisponível retorna `503 agent_unavailable`.
- [ ] Total é recalculado pelo servidor a partir dos snapshots do catálogo.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-10-31 | Draft | Story criada para fechar o fluxo persistente sem confiar cegamente na saída do agente. |
