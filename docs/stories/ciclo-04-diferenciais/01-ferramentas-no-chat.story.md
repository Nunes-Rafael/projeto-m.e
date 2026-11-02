# Story 1: Exibir ferramentas chamadas no chat

## Status

Done

## Módulo

Diferenciais opcionais

## Alocado a

Vegeta e Gohan

## Dependências

- Ciclo 03 concluído, incluindo contrato atual de resposta da API.
- Aprovação de Rafael para iniciar o Ciclo 04.

## Prioridade

Alta; pequeno esforço, alto valor para explicar MCP na demonstração.

## Contexto completo

O agente consulta o catálogo por MCP. Hoje o resultado mostra produtos e justificativa, mas não evidencia ao usuário quais ferramentas participaram. A evidência precisa vir da execução real, não de uma lista fixa na interface.

## O que fazer

Registrar no backend os nomes das ferramentas MCP chamadas durante uma única requisição e incluí-los na resposta de sucesso. Renderizar no painel de resultado uma lista discreta, incluindo `criar_requisicao` quando essa tool realmente for executada, sem argumentos internos, chaves ou payloads completos.

## Critérios de aceite

- [x] Uma resposta bem-sucedida inclui apenas tools efetivamente chamadas naquela execução.
- [x] O chat apresenta os nomes dessas tools no resultado da requisição, sem argumentos, payloads, credenciais ou identificadores internos.
- [x] A allowlist visual inclui `criar_requisicao` quando o backend a retorna como chamada executada; a UI não a inventa nem a omite.
- [x] Modo local e OpenAI/OpenRouter usam o mesmo contrato de telemetria.
- [x] A lista é reiniciada a cada envio; falha ou requisição seguinte não reutiliza tools de execução anterior.
- [x] Testes verificam resposta com uma tool, múltiplas tools (incluindo `criar_requisicao`), ferramenta desconhecida, estado vazio e falha, incluindo que a interface não mostre dados de execução anterior.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-11-02 | Approved | Rafael aprovou o Ciclo 04 e liberou esta story para execução. |
| 2026-11-02 | Review | Implementação de telemetria no backend e exibição no frontend reportada completa; alterações estão em `backend/app/agent.py`, `backend/app/main.py`, `frontend/src/App.jsx` e `frontend/src/styles.css`. Backend pytest não foi executado para evitar risco ao banco existente. |
| 2026-11-02 | Review | `npm install` concluiu sem vulnerabilidades reportadas; `npm run build` passou com Vite 8.3.5, e foi verificado que a lista de ferramentas allowlisted aparece e um novo envio limpa o resultado anterior. Backend pytest continua pendente até haver banco/fixture isolado; por isso, os critérios de integração backend seguem sem evidência e a story não está concluída. |
| 2026-11-02 | Review | Atualização de validação isolada: os 4 testes de UI passaram, build frontend passou e 2 testes unitários de backend passaram. Testes de integração com banco ainda estão pendentes; S1 continua em Review e não pode ser concluída até executá-los contra banco isolado. |
| 2026-11-02 | Review | Gohan executou integração backend em banco isolado: 16 testes passaram. Com os 4 testes de UI, build frontend e 2 testes unitários já registrados, as validações reportadas para S1 passaram. Aguarda revisão/QA final de Tanjiro; não marcada Done. |
| 2026-11-02 | Review | QA Tanjiro identificou que, após S4, a allowlist da UI omite `criar_requisicao`, embora a ferramenta possa vir na resposta. Vegeta está corrigindo e acrescentará teste. Manter Review até correção e nova evidência de teste/build confirmarem que a ferramenta aparece apenas quando retornada pelo backend. |
| 2026-11-02 | Done | Tanjiro confirmou a correção de Vegeta: allowlist inclui `criar_requisicao`, usa rótulo genérico e teste cobre três tools, ferramenta desconhecida, estados vazios, falha e limpeza. Evidências: 4 testes UI + build, 2 testes unitários backend isolados e 16 testes de integração DB isolado passaram. Critérios de aceite concluídos. |
