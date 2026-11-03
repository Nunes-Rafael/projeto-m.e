# Story 1: Avaliação opt-in do agente com LLM real

## Status

InProgress — orçamento de US$ 0,50 por execução aprovado; implementação em andamento. Execução real pendente.

## Módulo

Avaliação do agente

## Responsáveis e gates

- Senku: arquitetura em `docs/architecture/AVALIACAO-LLM-ARCH.md` (concluída).
- Levi: coordenação do Ciclo 05 e dependências (em andamento).
- Gohan: implementação no backend Python.
- Tanjiro: revisar critérios funcionais, isolamento e guard de custo antes da execução paga.
- Shinobu: atualizar README e registrar saída da avaliação após a execução.

## Dependências

- Ciclo 04 concluído.
- PRD e arquitetura aprovados e registrados.
- Provedor OpenAI e modelo `OPENAI_MODEL` configurados localmente; modelo confirmado como `gpt-5.4-nano` sem expor a chave.
- Limite de custo de US$ 0,50 por execução aprovado por Rafael.
- Cinco cenários, catálogo sintético, gravador em memória, limites e critérios objetivos registrados na arquitetura.

## Prioridade

Média — acrescenta evidência sobre decisões do modelo real, mantendo a CI sem chamadas pagas.

## Contexto

O PDF sugere cinco pedidos para mostrar quantos o agente acertou. A avaliação atual usa fixtures de agente determinísticas. Esta story executará o `PurchaseAgent` real com o modelo configurado, mas manterá catálogo e persistência em fixtures isoladas.

## Contrato de execução

Adicionar modo explicitamente opt-in com `--live --confirm-paid --max-cost-usd 0.50` ao comando `python -m evaluation.run`. O modo normal continuará determinístico. O modo real lerá `AGENT_MODE`, `OPENAI_API_KEY` e `OPENAI_MODEL` do ambiente; usará cinco pedidos sintéticos, catálogo controlado e gravador em memória; obterá o agente por `get_purchase_agent()` e chamará `decide` diretamente, sem percorrer `POST /requisicoes`, `TestClient` ou o adaptador MCP; validará regras de produto, quantidade, teto e total; reportará resultados, tokens e reserva/estimativa de custo sem imprimir prompts, respostas completas, headers ou chave.

Limites obrigatórios: até cinco cenários, seis chamadas ao provedor por cenário, 512 tokens de saída por chamada, 32 KiB de corpo por request e preflight de custo. O máximo aprovado de US$ 0,50 por execução é um teto para a reserva/estimativa do programa, não uma garantia do valor faturado pela OpenAI. Falhar fechado para modelo sem preço conhecido, reserva projetada que exceda o valor solicitado, usage ausente, provedor indisponível ou configuração incompleta. Não fazer retries automáticos. Nunca chamar o banco/MCP de demonstração nem DummyJSON. A avaliação paga só pode ser iniciada pelo comando `--live --confirm-paid --max-cost-usd 0.50`; não executá-la na CI.

## Critérios de aceite

- [ ] `python -m evaluation.run` continua executando apenas os cinco cenários determinísticos e não exige chave/rede.
- [ ] `python -m evaluation.run --live --confirm-paid --max-cost-usd 0.50` é o único caminho ao modo pago e valida modo OpenAI, chave, modelo e os dois opt-ins.
- [ ] O modo pago executa no máximo cinco pedidos com o modelo configurado no `.env`, usando fixtures de catálogo e persistência em memória.
- [ ] Cada caso verifica produto aceito, quantidade, teto unitário, total recalculado e persistência simulada.
- [ ] O agente é chamado diretamente com fixtures; o processo não usa endpoint HTTP/`TestClient` e não conecta ao PostgreSQL/MCP nem ao catálogo externo.
- [ ] O preflight usa limites de request/tokens e tarifa conhecida com margem; recusa antes de enviar se a reserva estimada exceder US$ 0,50.
- [ ] Ausência de usage ou tarifa/modelo conhecido falha fechado, sem tentativa de contornar o limite.
- [ ] A saída não contém chave, headers, request/response completos ou prompts; mostra modelo, tokens, estimativa, resultado por caso e `N/5`.
- [ ] O modo real não é executado na CI; CI permanece sem segredos, tráfego de modelo ou custo.
- [ ] README descreve ambos os modos, pré-requisitos, limites, custo e diferença entre fixture/live.
- [ ] Tanjiro revisa a implementação e confirma estaticamente que o modo real injeta fixtures, não conecta a PostgreSQL/MCP/DummyJSON e respeita o teto antes de cada chamada.
- [ ] Uma execução real autorizada por Rafael reporta usage e reserva/estimativa; a reserva do programa nunca excede US$ 0,50. A documentação deixa claro que isso não limita absolutamente a cobrança efetiva.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-11-03 | Approved | Rafael aprovou a extensão, definiu o limite de US$ 0,50 por execução e autorizou usar o modelo configurado em `.env`. |
| 2026-11-03 | InProgress | Senku concluiu a arquitetura. Levi organizou o ciclo; Gohan implementa o modo opt-in. Nenhuma chamada paga foi feita. Tanjiro revisará isolamento e custo antes da execução autorizada. |
| 2026-11-03 | InProgress | Tanjiro aprovou a revisão estática: opt-in CLI exige `--live --confirm-paid --max-cost-usd`; só o adaptador OpenAI faz rede, enquanto busca/detalhe/gravação usam fixtures e memória; guarda reserva custo estimado antes de cada chamada, sem retries; saída não imprime pedidos, respostas completas, headers ou chave; cinco cenários verificam produto, quantidade, teto, total e uma gravação simulada. Nenhum teste foi criado ou executado e nenhuma chamada paga foi feita nesta revisão. A execução autorizada ainda é necessária para concluir a story. |
