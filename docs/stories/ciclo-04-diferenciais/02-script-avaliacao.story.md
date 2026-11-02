# Story 2: Script de avaliação com cinco pedidos

## Status

Draft

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

- [ ] Os cinco casos identificados acima têm entrada, fixtures, expectativa e regra verificada documentadas.
- [ ] Um único comando documentado executa os cinco casos sem chamar OpenAI, OpenRouter ou DummyJSON real.
- [ ] A saída informa para cada caso aprovado/reprovado e motivo, além do total `N/5`; código de saída é zero somente quando todos passam.
- [ ] Duas execuções com as mesmas fixtures produzem os mesmos resultados e não criam registros no banco de demonstração.
- [ ] README documenta comando, pré-requisitos, resultado esperado e limite de que a avaliação mede critérios explícitos, não qualidade geral de respostas do modelo.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-11-02 | Draft | Story detalha o diferencial do script de avaliação, priorizando regras observáveis e isolamento dos dados locais. |
