# Story 1: Exibir ferramentas chamadas no chat

## Status

Draft

## Módulo

Diferenciais opcionais

## Alocado a

Vegeta e Gohan

## Dependências

Ciclo 03 concluído.

## Prioridade

Alta; pequeno esforço, alto valor para explicar MCP na demonstração.

## Contexto completo

O agente consulta o catálogo por MCP. Hoje o resultado mostra produtos e justificativa, mas não evidencia ao usuário quais ferramentas participaram. A evidência precisa vir da execução real, não de uma lista fixa na interface.

## O que fazer

Registrar no backend os nomes das ferramentas MCP chamadas durante uma única requisição e incluí-los na resposta de sucesso. Renderizar no painel de resultado uma lista discreta, por exemplo `buscar_produtos` e `detalhar_produto`, sem argumentos internos, chaves ou payloads completos.

## Critérios de aceite

- [ ] Uma resposta bem-sucedida inclui apenas tools efetivamente chamadas naquela execução.
- [ ] O chat mostra os nomes das tools sem exibir argumentos ou dados sensíveis.
- [ ] Modo local e OpenAI/OpenRouter usam o mesmo contrato de telemetria.
- [ ] Falhas não mostram tools de uma requisição anterior.
- [ ] Testes cobrem execução com uma tool, duas tools e nenhuma persistência em falha.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-11-02 | Draft | Story proposta para tornar o uso do MCP visível na demonstração sem introduzir detalhes internos desnecessários. |
