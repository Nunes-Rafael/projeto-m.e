# Story 2: Script de avaliação com cinco pedidos

## Status

Draft

## Módulo

Diferenciais opcionais

## Alocado a

Tanjiro e Gohan

## Dependências

Story 1; backend e modo local disponíveis.

## Prioridade

Alta; torna o comportamento demonstrável de forma repetível.

## Contexto completo

O case sugere um script com cinco pedidos e uma contagem de acertos. O modo local evita chave e custo. Resultados de LLM variam, então a avaliação deve verificar propriedades e critérios de negócio, não exigir uma frase ou produto específico quando existirem várias respostas válidas.

## O que fazer

Criar cinco cenários cobrindo sucesso com teto e quantidade, termo de produto diferente, produto acima do teto, busca sem resultado e erro recuperável do catálogo. O script prepara dependências de teste, executa os casos isoladamente e imprime `N/5` com detalhe por caso. Não deve contaminar o banco de demonstração; usar banco temporário/teste ou limpeza transacional segura.

## Critérios de aceite

- [ ] Os cinco casos têm entrada, expectativa e justificativa documentadas.
- [ ] A execução padrão não chama OpenAI, OpenRouter ou DummyJSON real.
- [ ] O resumo mostra total de aprovados e falhas com motivo.
- [ ] Reexecuções são determinísticas e não deixam registros no banco de demonstração.
- [ ] README documenta comando, pré-requisitos e interpretação do resultado.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-11-02 | Draft | Story detalha o diferencial do script de avaliação, priorizando regras observáveis e isolamento dos dados locais. |
