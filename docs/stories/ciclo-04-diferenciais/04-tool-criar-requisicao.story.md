# Story 4: Tool MCP para criar requisição

## Status

Draft — requer aprovação de arquitetura antes de implementação.

## Módulo

Diferenciais opcionais

## Alocado a

Senku, Merlin, Gohan, Jin-Woo e Gojo

## Dependências

Stories 1–3; decisão técnica aprovada e revisão de segurança antes de codificar.

## Prioridade

Opcional avançado; maior valor técnico e maior risco de integridade.

## Contexto completo

O desafio propõe opcionalmente `criar_requisicao` como terceira ferramenta MCP para que o modelo decida quando salvar. Hoje o backend valida a decisão do agente e persiste diretamente. A nova ferramenta não pode receber valores confiados cegamente do modelo nem permitir duplicidade ou gravação de itens não encontrados no catálogo da execução.

## O que fazer

Especificar e, após aprovação, implementar `criar_requisicao` no servidor MCP com uma fronteira segura de persistência. Antes de executar, o backend deve validar origem de cada produto, quantidade, preço unitário máximo, cálculo monetário e consistência dos itens. O modelo pode solicitar a tool, mas a política de validação e o commit transacional permanecem determinísticos. Definir comportamento de retries/idempotência, resposta da ferramenta e como a API apresenta a requisição criada sem gravar duas vezes.

## Critérios de aceite

- [ ] Arquitetura define responsabilidades entre backend, agente, MCP e banco antes da implementação.
- [ ] Tool rejeita item não originado no catálogo desta execução, preço alterado/incompatível e quantidade inválida.
- [ ] Falhas em qualquer item não deixam cabeçalho nem itens parciais no banco.
- [ ] Retry da mesma chamada não cria duplicata, ou o contrato documenta e testa a estratégia idempotente escolhida.
- [ ] Testes cobrem tool call, recusa de persistência, falha transacional e sucesso.
- [ ] Revisão de segurança aprova antes de marcar como concluída.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-11-02 | Draft | Story separada por alterar a autoridade de persistência; execução depende de arquitetura e gate de segurança próprios. |
