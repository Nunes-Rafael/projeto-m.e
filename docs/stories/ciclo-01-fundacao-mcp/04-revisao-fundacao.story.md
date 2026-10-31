# Story 4: Revisão de integração e segredos

## Status

Done

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
| 2026-10-31 | Review (Gojo) | Revisados `compose.yaml`, `.gitignore`, `.env.example` e o MCP. Não há segredo versionado; a chave de LLM só entra no backend e erros externos do catálogo retornam mensagem segura. As duas tools validam schemas e usam timeout de 3 s. Achados: a porta 8001 do MCP está publicada no host sem necessidade para o fluxo interno, e os defaults de banco usam `change-me`; ambos devem ser restringidos antes de qualquer exposição fora do ambiente local. |
| 2026-10-31 | Review | Near revisou `compose.yaml`, contratos MCP e a suíte: `docker compose config` e 4 testes passaram. Não há segredo versionado, o frontend não recebe credenciais e o timeout de 3 s converte falha de rede em resposta segura. **Achado alto:** o serviço expõe endpoints HTTP próprios (`POST /tools/...`), mas ainda não implementa o protocolo/SDK MCP; isso precisa ser resolvido antes de alegar conformidade com o requisito de servidor MCP. **Achado médio:** a suíte cobre timeout e validação, mas ainda não cobre HTTP 5xx e payload externo inválido, cenários explicitados na arquitetura. |
| 2026-10-31 | Review | Correções aplicadas: SDK MCP com Streamable HTTP respondeu `initialize` com 200; suíte ampliada para HTTP 5xx e payload inválido, totalizando 6 testes. A porta MCP foi retirada do host e a senha do Postgres passou a ser obrigatória por ambiente. |
| 2026-10-31 | Done (Near) | Revisão final confirmou Streamable HTTP real em `/mcp`: uma chamada JSON-RPC `initialize` retornou 200 e declarou a capacidade `tools`. A suíte executou 6 testes sem rede/LLM, cobrindo timeout, HTTP 5xx e payload inválido; `docker compose up -d` deixou os quatro serviços saudáveis com variável de senha definida. Sem bloqueios de qualidade remanescentes para este ciclo. |
| 2026-10-31 | Sign-off (Gojo) | Revisão pós-correção no commit `e40e45a`: MCP não publica mais porta no host; `POSTGRES_PASSWORD` é obrigatório no Compose; `.env` e `Case-FDE.pdf` não estão rastreados. Nenhum bloqueio crítico de segurança permanece para o escopo local deste ciclo. |
