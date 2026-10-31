# Story 2: Servidor MCP e ferramentas de catálogo

## Status

Approved

## Módulo

Fundação e MCP

## Alocado a

Gohan

## Dependências

Story 1 concluída.

## Prioridade

Crítica.

## Contexto completo

Somente o servidor MCP pode chamar DummyJSON. Ele expõe `buscar_produtos(termo)` e `detalhar_produto(id)` por HTTP. Busca aceita termo entre 2 e 120 caracteres e normaliza produtos. Detalhe aceita identificador inteiro positivo. A API externa possui timeout de 3 segundos; rede, resposta inválida e HTTP 5xx devem produzir erro seguro, sem detalhes internos.

## O que fazer

Implementar o servidor MCP em Python, seu cliente HTTP de catálogo e as duas ferramentas. Não implementar agente, banco, endpoints de requisição ou frontend neste ciclo.

## Critérios de aceite

- [ ] `buscar_produtos` usa o endpoint de busca do DummyJSON e retorna somente o contrato normalizado.
- [ ] `detalhar_produto` usa o endpoint de detalhe e retorna dados úteis ao agente.
- [ ] Entradas inválidas são rejeitadas antes de chamar a rede.
- [ ] Timeout, HTTP 5xx e payload inválido são convertidos em erro seguro e previsível.
- [ ] Nenhuma ferramenta contém chave, prompt ou regra de seleção de compra.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-10-31 | Draft | Story criada para isolar a integração de catálogo do futuro loop do agente. |
