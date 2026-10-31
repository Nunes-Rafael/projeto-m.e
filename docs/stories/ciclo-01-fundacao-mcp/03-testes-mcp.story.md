# Story 3: Testes independentes do MCP

## Status

Review

## Módulo

Fundação e MCP

## Alocado a

Tanjiro

## Dependências

Story 2 concluída.

## Prioridade

Crítica.

## Contexto completo

O case exige um teste para cada ferramenta MCP, sem chave de LLM. Os testes não podem depender da disponibilidade da DummyJSON; devem usar transporte HTTP simulado ou fixture controlada. O comportamento relevante é o contrato público das tools, não detalhes internos de implementação.

## O que fazer

Criar a suíte de testes do servidor MCP e os fixtures necessários. Cobrir resposta válida, validação de entrada e indisponibilidade/timeout do catálogo.

## Critérios de aceite

- [ ] Existe teste independente e executável para `buscar_produtos`.
- [ ] Existe teste independente e executável para `detalhar_produto`.
- [ ] Nenhum teste exige `OPENROUTER_API_KEY` ou rede externa.
- [ ] Falhas externas são verificadas sem expor detalhes internos.
- [ ] O comando de testes é documentável no README.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-10-31 | Draft | Story criada para garantir a exigência de validação independente do LLM. |
| 2026-10-31 | Review | Adicionada a suíte `mcp-server/tests/test_catalog_tools.py` com mocks assíncronos do catálogo para busca, detalhe, validação local e timeout; os testes exercitam o contrato HTTP sem rede ou chave de LLM. |
