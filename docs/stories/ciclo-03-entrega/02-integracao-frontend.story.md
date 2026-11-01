# Story 2: Integração de API e estados reais

## Status

Approved

## Módulo

Interface e entrega final

## Alocado a

Vegeta

## Dependências

Story 1 concluída.

## Prioridade

Crítica.

## Contexto completo

`POST /requisicoes` retorna requisição criada ou envelope de erro estável. `GET /requisicoes` retorna lista por data descrescente. Códigos relevantes: 422 para validação, ambiguidade, incompatibilidade e resultado inválido; 503 para catálogo ou agente indisponível. O texto digitado precisa ser preservado em erro recuperável.

## O que fazer

Conectar os componentes à API do backend, tratando estados HTTP e atualizando o histórico após sucesso. O frontend não calcula totais, seleciona produtos ou acessa catálogo diretamente.

## Critérios de aceite

- [ ] Formulário envia pedido para `POST /requisicoes` e exibe resposta real.
- [ ] Histórico busca `GET /requisicoes` e mostra no máximo cinco entradas.
- [ ] Estados 422 e 503 mostram mensagem apropriada e preservam pedido quando aplicável.
- [ ] Sucesso atualiza painel e histórico sem recarregar a página.
- [ ] URL do catálogo, banco e segredos não aparecem no frontend.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-10-31 | Draft | Story criada para conectar somente o contrato HTTP público ao frontend. |
