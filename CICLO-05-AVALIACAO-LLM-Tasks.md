# Ciclo 05 — Avaliação do agente com LLM real

## Cycle Goal

Medir como o modelo OpenAI configurado decide em cinco pedidos de compra sintéticos, com critérios verificáveis, sem gravar no banco demonstrativo e mantendo a reserva/estimativa do programa até US$ 0,50 por execução.

## Status

Review — implementação e execução live concluídas; falta cobertura automatizada específica do guard de custo/configuração.

## Definition of Ready

- PRD atualizado com a lacuna e a extensão aprovada.
- Arquitetura em `docs/architecture/AVALIACAO-LLM-ARCH.md` define cenários, isolamento e preflight de custo.
- Rafael aprovou o limite de US$ 0,50 por execução e o uso do modelo `OPENAI_MODEL` configurado no `.env`.
- Não há mudança de UI, banco ou coleta de dados pessoais.
- A execução live não faz parte da CI e não é iniciada automaticamente.

## Stories e sequência de trabalho

| # | Trabalho | Responsável | Status | Dependências |
|---|---|---|---|---|
| 1 | [Avaliação opt-in do agente real](docs/stories/ciclo-05-avaliacao-llm/01-avaliacao-agente-real.story.md) — CLI, fixtures isoladas e preflight de custo | Gohan | Review | Implementação entregue; testes automatizados específicos pendentes |
| 2 | Revisar estaticamente isolamento de efeitos, proteção da chave, limites de chamadas/tokens e critérios de pontuação | Tanjiro | Done | Revisão estática aprovada sem achados bloqueantes |
| 3 | Executar uma avaliação autorizada com `--live --confirm-paid --max-cost-usd 0.50`, usando apenas `OPENAI_MODEL` | Iroh, sob autorização já concedida | Done | 5/5; reserva estimada abaixo do teto |
| 4 | Registrar resultado, uso/tokens e limites no README e na story | Shinobu | Done | Resultado live documentado |

## Gate de saída

- O modo padrão continua determinístico e não chama provedor.
- A avaliação live usa o agente real com catálogo e persistência em memória; nenhuma conexão ao PostgreSQL, MCP ou DummyJSON.
- O guard reserva custo estimado antes de cada chamada e bloqueia se a reserva exceder US$ 0,50; esse limite não promete limitar absolutamente a cobrança efetiva do provedor.
- QA revisa isolamento, não exposição de chave e saída resumida.
- Uma única execução live autorizada termina ou falha de forma segura; uso e custo estimado são registrados sem conteúdo sensível.
- README explica como diferenciar a avaliação determinística da execução paga opt-in.
- A story permanece em Review até existir cobertura automatizada específica do guard de custo e configuração.

## Risco e limite

A estimativa usa preço conhecido do modelo configurado e margem; o valor final do provedor pode variar. Mudança de modelo, preço ou formato da chamada exige revisar o preflight antes de executar novamente. O modo live avalia o raciocínio do modelo sobre um catálogo controlado, não representa qualidade ou disponibilidade do catálogo real.

## Resultado da execução autorizada

Em 2026-11-03, a execução opt-in com `gpt-5.4-nano` concluiu os cinco cenários: **5/5 PASS**, em 13 chamadas ao provedor. O uso reportado foi 5.346 tokens de entrada e 456 de saída; a estimativa com margem de 25% foi **US$ 0,00205**. O limite conservador calculado para a configuração foi US$ 0,30048 por execução. A avaliação usou catálogo e gravação em memória, sem acesso ao PostgreSQL, MCP ou DummyJSON reais. A cobrança efetiva pode divergir da estimativa. Testes automatizados específicos do guard ainda não foram criados nem executados.
