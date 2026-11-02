# Story 3: CI de lint e testes

## Status

Draft

## Módulo

Diferenciais opcionais

## Alocado a

Itachi e Tanjiro

## Dependências

- Stories 1 e 2 aprovadas e concluídas; seus comandos de lint, build e avaliação documentados e executáveis localmente.
- Aprovação de Rafael para iniciar o Ciclo 04.

## Prioridade

Média-alta; aumenta confiança e qualidade de entrega.

## Contexto completo

O pipeline deve validar o que pode ser verificado sem serviço externo. Não pode exigir credenciais OpenAI/OpenRouter nem consumir saldo da API. O projeto é entregue como repositório Git com histórico legível.

## O que fazer

Adicionar GitHub Actions para lint/build do frontend, testes Python do backend e MCP, validação do Compose e verificação básica de segredos. Fixar versões/dependências necessárias para que a execução seja reproduzível. Não fazer deploy ou publicar artefatos.

## Critérios de aceite

- [ ] Workflow executa em pull request e push para `main`.
- [ ] Workflow executa lint e build do frontend e retorna falha se qualquer comando falhar.
- [ ] Workflow executa testes do backend, MCP e os cinco cenários de avaliação sem chaves de provedor nem tráfego para catálogo externo.
- [ ] Validação do Compose usa apenas placeholders explícitos e não publica imagens nem inicia deploy.
- [ ] Cada etapa tem nome identificável e qualquer falha torna o workflow malsucedido.
- [ ] README descreve verificações executadas e informa que CI não valida chamadas reais ao provedor/modelo.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-11-02 | Draft | Story transforma as verificações locais em evidência automatizada no repositório. |
