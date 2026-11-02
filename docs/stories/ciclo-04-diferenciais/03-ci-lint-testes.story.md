# Story 3: CI de lint e testes

## Status

Review — workflow criado e comandos verificados localmente; execução no GitHub ainda não verificada.

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

- [x] Workflow configurado para pull request e push para `main`; configuração validada localmente com `actionlint 1.7.7`. Execução no GitHub ainda pendente.
- [x] Workflow executa lint, testes e build do frontend e retorna falha se qualquer comando falhar; os comandos passaram localmente.
- [x] Workflow executa testes do backend, MCP e os cinco cenários de avaliação sem chaves de provedor nem tráfego para catálogo externo; suites completas passaram em PostgreSQL descartável.
- [x] Validação do Compose usa apenas placeholders explícitos e não publica imagens nem inicia deploy; `docker compose --env-file /dev/null config --quiet` passou.
- [x] Cada etapa tem nome identificável e qualquer falha torna o workflow malsucedido; shell Bash preserva falhas e não há `continue-on-error`.
- [x] README descreve comandos locais, o que é verificado na CI e que chamadas reais ao modelo/catálogo externo não são testadas.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-11-02 | Approved | Rafael aprovou o Ciclo 04 e liberou esta story para execução após Stories 1 e 2 estabilizarem seus comandos. |
| 2026-11-02 | Approved | Stories 1 e 2 estão Done; pré-requisitos e comandos estão estabilizados. Story 3 liberada formalmente para execução. |
| 2026-11-02 | Review | Workflow criado para frontend, Python com Postgres de teste e Compose. Localmente: lint, 4 testes e build do frontend; 26 testes backend; 20 testes MCP; avaliação 5/5; Compose config válido. Execução no GitHub e revisão final pendentes. |
| 2026-11-02 | Review | Retomada por Itachi: ações fixadas por SHA verificado no repositório oficial, Node `22.20.0`, Python `3.12.12`, Ubuntu `24.04` e imagem PostgreSQL por digest. `actionlint 1.7.7` passou. Frontend: lint exit 0 com 8 warnings conhecidos de configuração Biome/CSS, 4/4 testes e build passaram. Backend: 26/26 testes; MCP: 20/20, incluindo sanitização ampliada; avaliação: 5/5. PostgreSQL `purchase_test` exclusivo em container descartável, sem porta ou volume, e rede interna removidos após a execução. Nenhum acesso ao banco da demonstração ou API externa. |
| 2026-11-02 | Review | Scanner local `python scripts/check_secrets.py` verifica nomes de arquivos sensíveis e padrões conhecidos de credenciais, informando somente caminho e linha. Scan do repositório passou; uma credencial sintética foi detectada com exit 1 sem ecoar seu valor. Compose validado com placeholders e sem carregar `.env`. Workflow não foi executado no GitHub; revisão final e atualização documental permanecem como gate. |
| 2026-11-02 | Review | README atualizado com workflow, comandos e limites da CI. `actionlint 1.7.7`, frontend, backend, MCP, avaliação, scanner e Compose passaram localmente; lint frontend emitiu 8 warnings não bloqueantes de configuração Biome/CSS. A execução remota no GitHub não foi feita; Story permanece Review até essa evidência externa. |
