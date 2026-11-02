# Story 3: CI de lint e testes

## Status

Draft

## Módulo

Diferenciais opcionais

## Alocado a

Itachi e Tanjiro

## Dependências

Stories 1 e 2; comandos locais estáveis.

## Prioridade

Média-alta; aumenta confiança e qualidade de entrega.

## Contexto completo

O pipeline deve validar o que pode ser verificado sem serviço externo. Não pode exigir credenciais OpenAI/OpenRouter nem consumir saldo da API. O projeto é entregue como repositório Git com histórico legível.

## O que fazer

Adicionar GitHub Actions para lint/build do frontend, testes Python do backend e MCP, validação do Compose e verificação básica de segredos. Fixar versões/dependências necessárias para que a execução seja reproduzível. Não fazer deploy ou publicar artefatos.

## Critérios de aceite

- [ ] Workflow roda em pull request e push para branch principal.
- [ ] Frontend compila e passa lint configurado.
- [ ] Testes de backend e MCP passam sem chaves nem chamadas externas.
- [ ] Compose valida sem iniciar serviços que exijam segredo real; placeholders de teste são explícitos.
- [ ] Falha em qualquer etapa deixa o workflow vermelho com etapa identificável.
- [ ] README mostra o que a CI verifica e seus limites.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-11-02 | Draft | Story transforma as verificações locais em evidência automatizada no repositório. |
