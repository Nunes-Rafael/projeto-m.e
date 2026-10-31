# Story 3: Adaptadores do agente local e OpenRouter

## Status

Review

## Módulo

Backend, persistência e agente

## Alocado a

Gohan

## Dependências

Story 2 concluída.

## Prioridade

Crítica.

## Contexto completo

O modo padrão é `local`, determinístico e voltado a desenvolvimento. O modo `openrouter` é ativado apenas com `OPENROUTER_API_KEY` e modelo configurado. No modo real, o modelo decide quais tools chamar; o backend limita a seis chamadas e não programa a sequência de busca/detalhe.

## O que fazer

Definir uma interface única de agente e implementar os adaptadores local e OpenRouter. O adaptador local deve exercitar a mesma interface sem alegar que substitui validação de tool-calling real.

## Critérios de aceite

- [ ] `AGENT_MODE=local` funciona sem chave de LLM.
- [ ] `AGENT_MODE=openrouter` falha de forma clara sem chave/modelo configurados.
- [ ] Adaptador OpenRouter recebe schemas de tools e respostas de tools, sem fluxo fixo no backend.
- [ ] Limite de seis chamadas é aplicado.
- [ ] Nenhuma chave é logada, exibida ou versionada.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-10-31 | Draft | Story criada para separar desenvolvimento sem segredo da execução real com tool-calling. |
| 2026-10-31 | Review | Criados adaptadores local determinístico e OpenRouter em `backend/app/agent.py`; o modo real recebe schemas e resultados de tools em loop limitado a seis chamadas, enquanto o modo local permanece explicitamente voltado a desenvolvimento sem chave. |
