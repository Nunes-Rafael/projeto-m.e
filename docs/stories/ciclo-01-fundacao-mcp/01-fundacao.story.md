# Story 1: Fundação do ambiente local

## Status

Approved

## Módulo

Fundação e MCP

## Alocado a

Itachi

## Dependências

Nenhuma.

## Prioridade

Crítica.

## Contexto completo

O projeto é um monorepo com `backend/`, `mcp-server/`, `frontend/` e Postgres. Os quatro serviços precisam iniciar via `docker compose up --build`. O desenvolvimento padrão não possui chave de LLM; `.env` não pode ser versionado e `.env.example` não pode conter segredos.

## O que fazer

Criar somente a fundação de execução: estrutura de diretórios, Dockerfiles, `compose.yaml`, variáveis de ambiente documentadas e healthchecks. Os serviços devem ter contratos de rede explícitos e o banco deve estar saudável antes de o backend aceitar tráfego.

## Critérios de aceite

- [ ] `docker compose up --build` cria e inicia os quatro serviços.
- [ ] Postgres possui volume persistente e healthcheck.
- [ ] Serviços internos recebem URLs por variáveis de ambiente; o frontend não recebe segredos.
- [ ] `.env.example` descreve todas as variáveis necessárias sem valores reais.
- [ ] Não há credenciais, PDF do case ou artefatos gerados no Git.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-10-31 | Draft | Story criada para estabelecer o ambiente reproduzível antes de implementar comportamento. |
