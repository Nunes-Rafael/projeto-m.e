# Story 4: Tool MCP para criar requisição

## Status

Draft — requer aprovação de Rafael para o ciclo, revisão técnica de Senku e aprovação explícita da especificação antes de qualquer implementação.

## Módulo

Diferenciais opcionais

## Responsáveis propostos

- Senku: produzir/revisar `docs/architecture/OPCIONAIS-ARCH.md` com alternativas, decisão recomendada, contratos, fluxo de dados, falhas e trade-offs.
- Gohan: implementação do backend e integração com a tool, somente após os gates.
- Jin-Woo: revisar persistência, transação e estratégia de idempotência definidas na arquitetura.
- Gojo: revisar ameaças, autorização de gravação e validação de dados antes da conclusão.
- Tanjiro: verificar critérios e cenários de teste da entrega.

## Dependências

- Ciclo 03 concluído, incluindo persistência atual e fluxo MCP.
- Aprovação de Rafael para iniciar o Ciclo 04.
- `docs/architecture/OPCIONAIS-ARCH.md` produzido por Senku, revisado pelos responsáveis técnicos e aprovado por Rafael antes de implementar.
- Revisão de segurança Gojo antes de concluir.
- Independente das Stories 1–3; telemetria, avaliação e CI não são pré-requisitos funcionais para a tool.

## Prioridade

Opcional avançado; maior valor técnico e maior risco de integridade.

## Contexto completo

O desafio propõe opcionalmente `criar_requisicao` como terceira ferramenta MCP para que o modelo decida quando salvar. Hoje o backend valida a decisão do agente e persiste diretamente. A nova ferramenta não pode receber valores confiados cegamente do modelo nem permitir duplicidade ou gravação de itens não encontrados no catálogo da execução.

## O que fazer

Senku deve primeiro registrar em `docs/architecture/OPCIONAIS-ARCH.md` a proposta de fluxo e contratos para `criar_requisicao`, incluindo autoridade de validação e gravação, prova/origem dos produtos, proteção de preço/quantidade, atomicidade, retry/idempotência, erros, observabilidade e trade-offs. Após revisão técnica e aprovação explícita de Rafael, implementar a decisão aprovada. O modelo pode solicitar gravação, mas não deve ser autoridade para validar catálogo, política de compra ou valores persistidos. A story não escolhe de antemão se a persistência ocorre no MCP ou por serviço interno chamado pelo MCP: a arquitetura deve decidir e justificar a fronteira.

## Critérios de aceite

- [ ] `docs/architecture/OPCIONAIS-ARCH.md` documenta componentes responsáveis, contratos de entrada/saída, fluxo de dados, validação, atomicidade, retry/idempotência, erros e trade-offs; Senku registra sua revisão técnica.
- [ ] Rafael registra aprovação explícita dessa especificação antes de iniciar implementação; status da story permanece Draft até essa aprovação.
- [ ] Implementação aceita somente produtos cuja origem e dados de preço possam ser validados pelo servidor contra o resultado autorizado da busca/detalhe; rejeita itens alterados, desconhecidos ou incompatíveis.
- [ ] Quantidade, limites de compra, moeda/precisão e total são validados/recalculados no servidor segundo regras aprovadas na arquitetura; valores fornecidos pelo modelo não são confiados.
- [ ] Qualquer falha na validação ou gravação resulta em zero requisições/itens parciais persistidos.
- [ ] Repetir a mesma operação conforme o contrato aprovado não duplica a requisição, e testes verificam o comportamento de retry/idempotência.
- [ ] Testes cobrem sucesso, recusa por item inválido, falha transacional e repetição; verificam estado persistido e resposta da API/tool.
- [ ] Gojo registra revisão de segurança sem achado bloqueador antes de marcar a story concluída.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-11-02 | Draft | Story separada por alterar a autoridade de persistência; Senku deve produzir a especificação técnica antes de revisão e aprovação de Rafael. Implementação e conclusão permanecem bloqueadas pelos gates listados. |
