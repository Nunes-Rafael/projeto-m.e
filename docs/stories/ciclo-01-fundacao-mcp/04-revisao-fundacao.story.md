# Story 4: Revisão de integração e segredos

## Status

Approved

## Módulo

Fundação e MCP

## Alocado a

Near e Gojo

## Dependências

Stories 1, 2 e 3 concluídas.

## Prioridade

Alta.

## Contexto completo

Este ciclo cria containers, conexão externa de catálogo e variáveis de ambiente. A aplicação ainda não coleta dados pessoais nem terá autenticação. A revisão deve verificar limites entre frontend, backend e MCP, além de impedir vazamento de segredos ou detalhes internos em erros.

## O que fazer

Revisar composição, configuração, contratos das ferramentas e testes. Reportar achados classificados e só liberar o ciclo sem falhas críticas.

## Critérios de aceite

- [ ] Nenhuma chave ou arquivo de ambiente foi versionado.
- [ ] Frontend não recebe URL de catálogo, credencial de banco ou credencial de LLM.
- [ ] Erros de rede não retornam stack trace ou headers ao cliente.
- [ ] As tools aceitam apenas schemas esperados e aplicam timeout.
- [ ] A revisão registra evidências ou achados acionáveis.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-10-31 | Draft | Story criada como gate de qualidade antes do ciclo de backend, persistência e UI. |
