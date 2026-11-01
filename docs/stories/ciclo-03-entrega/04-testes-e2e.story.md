# Story 4: Testes end-to-end

## Status

Approved

## Módulo

Interface e entrega final

## Alocado a

Tanjiro

## Dependências

Stories 1 e 2 concluídas.

## Prioridade

Alta.

## Contexto completo

O fluxo verificável é: abrir chat, enviar pedido, receber resposta estruturada e observar requisição no histórico. O ambiente local usa adaptador determinístico; testes não usam OpenRouter nem DummyJSON reais. Falhas de validação e indisponibilidade devem preservar a experiência definida no documento de design.

## O que fazer

Criar testes de ponta a ponta ou de fronteira equivalente para sucesso, erro de validação, incompatibilidade e falha temporária. Validar a apresentação de número, itens e total no fluxo bem-sucedido.

## Critérios de aceite

- [ ] Fluxo bem-sucedido cobre envio, resposta e atualização de histórico.
- [ ] Erro de validação mantém o pedido editável.
- [ ] Indisponibilidade apresenta ação de nova tentativa sem expor detalhes internos.
- [ ] Testes não exigem rede externa, chave ou intervenção manual.
- [ ] Comando de execução integra a documentação.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-10-31 | Draft | Story criada para provar o fluxo que será demonstrado, não detalhes internos de componentes. |
