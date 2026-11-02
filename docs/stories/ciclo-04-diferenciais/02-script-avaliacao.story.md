# Story 2: Script de avaliação com cinco pedidos

## Status

Done

## Módulo

Diferenciais opcionais

## Alocado a

Tanjiro e Gohan

## Dependências

- Ciclo 03 concluído; API e modo local disponíveis.
- Aprovação de Rafael para iniciar o Ciclo 04.
- Independente da Story 1: o script avalia resultados de negócio pela API, não a telemetria exibida no chat.

## Prioridade

Alta; torna o comportamento demonstrável de forma repetível.

## Contexto completo

O case sugere um script com cinco pedidos e uma contagem de acertos. O modo local evita chave e custo. Resultados de LLM variam, então a avaliação deve verificar propriedades e critérios de negócio, não exigir uma frase ou produto específico quando existirem várias respostas válidas.

## O que fazer

Criar cinco cenários cobrindo: sucesso com teto e quantidade; termo alternativo para produto compatível; produto acima do teto; busca sem resultado; erro recuperável do catálogo. Documentar por cenário entrada, pré-condições/fixture, resultado esperado e regra verificada. Executar contra dependências controladas e isoladas, sem contaminar o banco de demonstração, e imprimir `N/5` com estado e motivo por caso. A escolha do produto deve ser validada por propriedades de negócio, não por correspondência textual rígida quando houver mais de uma resposta válida.

## Critérios de aceite

- [x] Os cinco casos identificados acima têm entrada, fixtures, expectativa e regra verificada documentadas.
- [x] Um único comando documentado executa os cinco casos sem chamar OpenAI, OpenRouter ou DummyJSON real.
- [x] A saída informa para cada caso aprovado/reprovado e motivo, além do total `N/5`; código de saída é zero somente quando todos passam.
- [x] Duas execuções com as mesmas fixtures produzem os mesmos resultados e não criam registros no banco de demonstração.
- [x] README documenta comando, pré-requisitos, resultado esperado e limite de que a avaliação mede critérios explícitos, não qualidade geral de respostas do modelo.
- [x] Limitação documentada: cenários usam fixtures determinísticas e não medem a seleção feita pelo agente real.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-11-02 | Approved | Rafael aprovou o Ciclo 04 e liberou esta story para execução. Independente da Story 1. |
| 2026-11-02 | Review | CLI e fixtures determinísticas implementadas; em container isolado, `python -m evaluation.run` resultou em 5/5 e 3 testes específicos passaram. Execução não usou provedor/catálogo externo nem banco PostgreSQL de demonstração. Mantida em Review, sem marcar a story concluída, até revisão dos artefatos e critérios. |
| 2026-11-02 | Review | Revalidada após adaptação ao contrato da Story 4: CLI 5/5 e 3 testes passaram em container sem rede e sem `DATABASE_URL`/`MCP_SERVER_URL`; writer executado com mock em memória. Mantida em Review, sem marcar concluída. |
| 2026-11-02 | Review | Revalidação atual: CLI 5/5 e 3 testes específicos passaram em container isolado, sem rede, banco ou MCP reais; writer mockado em memória. Aguarda revisão/QA final de Tanjiro; não marcada Done. |
| 2026-11-02 | Done | QA Tanjiro aprovou. CLI 5/5 e 3 testes passaram em container isolado sem rede, banco ou MCP reais; writer mockado em memória. Limitação: fixtures determinísticas avaliam regras explícitas e não medem a seleção real do agente. |
