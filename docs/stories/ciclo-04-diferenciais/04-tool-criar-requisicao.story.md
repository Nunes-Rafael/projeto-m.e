# Story 4: Tool MCP para criar requisição

## Status

Done — implementação, critérios técnicos e risco residual revisados por Senku, Jin-Woo, Gojo e Tanjiro para a demonstração local.

## Módulo

Diferenciais opcionais

## Responsáveis propostos

- Senku: arquitetura final registrada em `docs/architecture/OPCIONAIS-ARCH.md`; apoiar esclarecimentos de contrato durante execução.
- Gohan: implementação do backend e integração com a tool, somente após os gates.
- Jin-Woo: revisar persistência, transação e estratégia de idempotência definidas na arquitetura.
- Gojo: sign-off de segurança condicional para demo local concedido; risco residual documentado abaixo e em `docs/architecture/OPCIONAIS-ARCH.md`.
- Tanjiro: revisão/QA final aprovado para a demonstração local.

## Dependências

- Ciclo 03 concluído, incluindo persistência atual e fluxo MCP.
- Aprovação de Rafael para iniciar o Ciclo 04.
- Decisão de arquitetura já aprovada por Rafael: o servidor MCP pode receber responsabilidade de escrita no PostgreSQL.
- `docs/architecture/OPCIONAIS-ARCH.md` finalizado por Senku e sign-off de arquitetura/segurança Gojo concedido; critérios de aceite implementados e comprovados antes de concluir.
- Independente das Stories 1–3; telemetria, avaliação e CI não são pré-requisitos funcionais para a tool.
- Revisão/QA final de Tanjiro concluída para o escopo da demonstração local.

## Prioridade

Opcional avançado; maior valor técnico e maior risco de integridade.

## Contexto completo

O desafio propõe opcionalmente `criar_requisicao` como terceira ferramenta MCP para que o modelo indique quando salvar. O backend valida a intenção e os dados do catálogo; o MCP autenticado persiste a requisição. A ferramenta não confia em valores financeiros fornecidos pelo modelo nem permite duplicidade ou gravação de itens sem origem confirmada na execução atual.

## O que fazer

O fluxo definido em `docs/architecture/OPCIONAIS-ARCH.md` está implementado: o backend confirma proveniência de produto, valida preço/quantidade e monta o comando canônico; o servidor MCP exige autenticação, revalida o contrato e grava de forma atômica e idempotente. O modelo pode solicitar a criação, mas não valida catálogo, política de compra ou valores persistidos.

## Critérios de aceite

- [x] `docs/architecture/OPCIONAIS-ARCH.md` documenta componentes responsáveis, contratos de entrada/saída, fluxo de dados, validação, atomicidade, retry/idempotência, erros e trade-offs; Senku finalizou a especificação e Gojo deu sign-off de arquitetura/segurança.
- [x] Rafael aprovou o servidor MCP como responsável pela gravação no PostgreSQL; migração, chave idempotente, limites e contratos estão definidos na arquitetura.
- [x] Sign-offs de Senku (arquitetura) e Jin-Woo (dados) registrados; Gojo deu sign-off de segurança condicionado à documentação explícita do risco residual da demonstração local.
- [x] Risco residual para demo local documentado: o role runtime possui `SELECT` e `INSERT` nas tabelas de requisições/itens; se MCP ou credencial forem comprometidos, pode inserir requisições fabricadas e um item ligado a cabeçalho existente. O role não tem `UPDATE`, `DELETE`, DDL ou privilégios administrativos. Esse risco médio é aceito apenas para o cluster dedicado do case e não para produção.
- [x] Implementação aceita somente produtos cuja origem e dados de preço possam ser validados pelo servidor contra o resultado autorizado da busca/detalhe; rejeita itens alterados, desconhecidos ou incompatíveis.
- [x] Quantidade, limites de compra, moeda/precisão e total são validados/recalculados no servidor segundo regras aprovadas na arquitetura; valores fornecidos pelo modelo não são confiados.
- [x] Fail-closed: chamadas sem segredo de serviço, com segredo inválido ou sem configuração são rejeitadas antes de qualquer SQL e não deixam registros.
- [x] Grants efetivos do usuário runtime do MCP são mínimos, sem ownership ou privilégios administrativos; migrações usam credencial separada.
- [x] Qualquer falha na validação ou gravação resulta em zero requisições/itens parciais persistidos; teste de falha ao inserir item prova rollback do cabeçalho e de todos os itens.
- [x] Retry idempotente concorrente: chamadas simultâneas com mesma chave e payload devolvem a mesma requisição; mesma chave com payload diferente retorna conflito estável, sem duplicatas nem linhas parciais.
- [x] Logs e respostas sanitizam segredo/token, header, prompt, payload financeiro, dados de produto e detalhes internos de exceção/SQL nos testes executados com nível INFO.
- [x] Teste explícito confirma que sentinel de senha do banco não vaza na resposta nem nos logs.
- [x] Testes explícitos cobrem sanitização de token/header, prompt, dados de produto e payload financeiro em respostas e logs.
- [x] Testes explícitos confirmam chamadas sem token e com token inválido são rejeitadas antes de SQL, sem alteração de linhas, e chamada autenticada válida persiste requisição/itens.
- [x] Teste de grants efetivos cobre ambas as tabelas (`requisicoes` e `itens_requisicao`): runtime tem `SELECT`/`INSERT` e não tem `UPDATE`/`DELETE`; sequence tem `USAGE`/`SELECT`, sem `UPDATE`.
- [x] Testes cobrem sucesso, recusa por item inválido, falha transacional e repetição; verificam estado persistido e resposta da API/tool.
- [x] Evidências automatizadas cobrem fail-closed, grants efetivos, concorrência/idempotência, rollback e sanitização dos dados sentinela em resposta e logs.
- [x] Tanjiro concluiu a revisão/QA final e aprovou a Story para a demonstração local.

**Limite de validação de logs:** os testes de sanitização capturam logs no nível INFO. O nível DEBUG do SDK MCP não foi avaliado; não trate essa evidência como certificação de logs em DEBUG ou autorização para produção.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-11-02 | Approved | Rafael aprovou o Ciclo 04 e a escrita MCP no PostgreSQL; Senku finalizou a arquitetura e Gojo deu sign-off de arquitetura/segurança. Liberada para implementação, com critérios de segurança ainda não implementados e obrigatórios para aceite. |
| 2026-11-02 | Review | Gohan reportou MCP 18/18, grants + telemetria S1 16/16, contratos backend + avaliação 10/10 e CLI 5/5 em execuções isoladas. Senku aprovou arquitetura, Jin-Woo deu sign-off de dados e Gojo concedeu sign-off de segurança condicional para demo local. O risco residual está registrado acima. Aguarda revisão/QA final de Tanjiro; não marcada Done. |
| 2026-11-02 | Review | QA Tanjiro identificou cobertura ainda necessária, apesar das suítes reportadas: testes explícitos de sanitização, rejeição sem/com token inválido antes de SQL, escrita válida autenticada e grants efetivos incluindo `itens_requisicao`. Status permanece Review até as lacunas receberem evidência e Tanjiro concluir QA final. |
| 2026-11-02 | Review | Gohan completou cobertura em Postgres efêmero: 20 testes MCP passaram, incluindo HTTP fail-closed sem/com token inválido (nenhuma conexão psycopg e zero linhas), gravação válida autenticada (cabeçalho + item), rollback/idempotência e sanitização do sentinel de senha do banco em resposta/log; 7 testes de grants passaram, verificando nas duas tabelas `SELECT`/`INSERT` permitidos e `UPDATE`/`DELETE` negados, além de privilégios da sequence. O banco efêmero foi removido. Gap de QA: sanitização ainda não cobre token/header, prompt, produto ou dados financeiros. Aguarda ampliação dessas asserções e QA final de Tanjiro antes de Done. |
| 2026-11-02 | Review | Teste ampliado de sanitização executado com token, prompt, produto e valor sentinelas em resposta e logs. Suíte MCP: 20 passaram; backend: 26 passaram, incluindo testes de grants, em Postgres descartável removido após os testes. QA final independente permanece pendente. |
| 2026-11-02 | Done | Tanjiro aprovou a Story para a demonstração local. Evidências: MCP 20/20 e grants backend 7/7 em PostgreSQL `*_test` descartável; backend 26/26, avaliação 5/5 e quatro testes UI também passaram. Testes de sanitização verificam token/header, prompt, produto, valor financeiro e erro interno em resposta/logs INFO; logs DEBUG do SDK MCP não foram avaliados. O risco residual da role MCP e a alternativa de produção estão documentados neste arquivo e em `OPCIONAIS-ARCH.md`. Nenhum dado do banco da demonstração foi usado. |
