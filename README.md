# Agente de Compras MCP

Aplicação demonstrativa que transforma um pedido em linguagem natural em uma requisição de compra baseada em catálogo, com itens, quantidades e valores persistidos.

## Executar localmente

Requisitos: Docker e Docker Compose.

```bash
cp .env.example .env
```

Edite `.env` e defina valores locais distintos para `POSTGRES_PASSWORD`, `PURCHASE_API_DB_PASSWORD`, `MCP_DB_PASSWORD` e `MCP_WRITE_TOKEN`. O modo padrão é `AGENT_MODE=local`, sem chave de LLM.

```bash
docker compose up --build
```

Abra <http://localhost:5173>. A API fica em <http://localhost:8000>; o servidor MCP é interno à rede do Compose. Para encerrar, use `Ctrl+C`; acrescente `-d` para executar em background e `docker compose down` para parar os serviços.

O serviço `db-migrate` cria as tabelas e configura as permissões antes da inicialização da aplicação. Ele usa a credencial de proprietário; o backend recebe uma credencial somente de leitura, e o MCP recebe uma credencial de leitura e inserção nas tabelas de requisições. O volume `postgres_data` preserva os dados entre reinicializações. Para uma demonstração limpa, `docker compose down -v` remove esse volume e os dados locais.

## Configuração

| Variável | Uso | Padrão |
|---|---|---|
| `POSTGRES_DB` | Nome do banco | `purchase_agent` |
| `POSTGRES_USER` | Usuário do banco | `purchase_agent` |
| `POSTGRES_PASSWORD` | Senha local do banco | Obrigatória em `.env` |
| `PURCHASE_API_DB_USER` / `PURCHASE_API_DB_PASSWORD` | Credenciais de leitura do backend | Senha obrigatória |
| `MCP_DB_USER` / `MCP_DB_PASSWORD` | Credenciais de persistência do servidor MCP | Senha obrigatória |
| `MCP_WRITE_TOKEN` | Token compartilhado entre backend e servidor MCP | Obrigatório |
| `MCP_SERVER_URL` | Endereço interno do servidor MCP | `http://mcp-server:8001` |
| `AGENT_MODE` | Adaptador do agente: `local`, `openrouter` ou `openai` | `local` |
| `OPENROUTER_API_KEY` | Chave do provedor no modo OpenRouter | Vazia |
| `OPENROUTER_MODEL` | Modelo com suporte a tool-calling | Vazio |
| `OPENAI_API_KEY` | Chave da API OpenAI quando `AGENT_MODE=openai` | Vazia |
| `OPENAI_MODEL` | Modelo OpenAI com suporte a tool-calling | Configurado em `.env.example` |
| `VITE_API_BASE_URL` | URL da API vista pelo navegador | `http://localhost:8000` |

O modo `local` permite desenvolver e demonstrar o fluxo sem credencial de LLM; sua seleção de produto é determinística e não representa decisão de um modelo. Para tool-calling real pela OpenAI, configure `AGENT_MODE=openai`, `OPENAI_API_KEY` e `OPENAI_MODEL` no `.env`. Para OpenRouter, use `AGENT_MODE=openrouter`, `OPENROUTER_API_KEY` e `OPENROUTER_MODEL`. Nunca coloque credenciais no frontend ou em arquivos versionados. `.env` e o PDF do enunciado são ignorados pelo Git.

## O que a aplicação faz

- O chat envia pedidos para `POST /requisicoes` e apresenta a resposta estruturada.
- O backend consulta o catálogo somente pelo protocolo MCP.
- As ferramentas MCP `buscar_produtos` e `detalhar_produto` consultam a API de demonstração DummyJSON.
- O agente solicita `criar_requisicao` com IDs e quantidades. O backend confirma que os produtos vieram da busca daquela execução, reconsulta seus detalhes, aplica o teto unitário e recalcula os valores.
- O backend envia o comando canônico ao MCP com autenticação de serviço. O MCP valida novamente o contrato e persiste requisição e itens numa transação idempotente.
- O resultado mostra os nomes das ferramentas MCP executadas, incluindo `criar_requisicao`, sem expor argumentos ou credenciais.
- `GET /requisicoes` lista as requisições registradas.
- Falhas de catálogo, entradas inválidas e ausência de produto compatível recebem respostas distintas; uma compra inválida não é persistida.

## Testes

O workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) está configurado para pull requests e push em `main`. Ele executa lint, testes e build do frontend, testes do backend e MCP com PostgreSQL exclusivo de teste, avaliação determinística, validação do Compose com valores fictícios e verificação de arquivos e padrões de credenciais. A execução no GitHub ainda não foi verificada. As suítes usam catálogo e provedor simulados, sem consumo de API de modelos ou chamadas ao DummyJSON.

Com Node.js 22, os comandos do frontend são:

```bash
cd frontend
npm ci
npm run lint
npm test
npm run build
```

Para Python 3.12, use ambientes virtuais separados para `backend` e `mcp-server`, pois cada componente tem suas dependências fixadas. Dentro de cada diretório, instale `requirements.txt` e execute `python -m pytest -q`. Sem as variáveis de teste abaixo, os testes que exigem PostgreSQL são marcados como `skipped`; os testes de contrato e fixtures continuam executáveis.

Para incluir integração, permissões, concorrência e rollback, use um PostgreSQL descartável exclusivo. Em outro terminal, inicie-o sem volume persistente:

```bash
docker run --rm --name purchase-agent-test \
  -e POSTGRES_DB=purchase_agent_test \
  -e POSTGRES_PASSWORD=test_password \
  -p 127.0.0.1:55432:5432 postgres:16-alpine
```

Quando estiver pronto para conexões, defina `MIGRATION_TEST_DATABASE_URL=postgresql://postgres:test_password@localhost:55432/purchase_agent_test` ao executar os testes do backend e `MCP_TEST_DATABASE_URL` com a mesma URL ao executar os testes do MCP. O nome do banco precisa terminar em `_test`. Os testes criam roles, aplicam migrações e limpam dados nesse banco exclusivo. Execute as suítes sequencialmente e encerre com `docker stop purchase-agent-test`; o container será removido. O banco da demonstração não deve ser usado para esses testes.

No ambiente virtual do backend, dentro de `backend/`:

```bash
python -m pip install -r requirements.txt
MIGRATION_TEST_DATABASE_URL=postgresql://postgres:test_password@localhost:55432/purchase_agent_test python -m pytest -q
```

No ambiente virtual do MCP, dentro de `mcp-server/`:

```bash
python -m pip install -r requirements.txt
MCP_TEST_DATABASE_URL=postgresql://postgres:test_password@localhost:55432/purchase_agent_test python -m pytest -q
```

Na raiz do repositório, a verificação básica de credenciais e a validação da configuração usam:

```bash
python scripts/check_secrets.py
POSTGRES_PASSWORD=ci_postgres PURCHASE_API_DB_PASSWORD=ci_api MCP_DB_PASSWORD=ci_mcp MCP_WRITE_TOKEN=ci_token docker compose --env-file /dev/null config --quiet
```

O scanner verifica nomes de arquivos sensíveis e padrões conhecidos de chaves; não substitui uma auditoria completa. A validação do Compose verifica a configuração sem iniciar serviços.

### Avaliação determinística do agente

A avaliação executa cinco cenários pela API FastAPI, usando catálogo, agente e armazenamento em memória controlados. Não chama OpenAI, OpenRouter, DummyJSON nem PostgreSQL; assim, não altera o banco usado pela demonstração. Requer Python 3.12 e as dependências de `backend/requirements.txt`:

```bash
cd backend
python -m pip install -r requirements.txt
python -m evaluation.run
```

O comando mostra `PASS` ou `FAIL` e o motivo em cada cenário, seguido do total `N/5`. O código de saída é zero somente quando todos passam. Os casos cobrem: compra dentro do teto com quantidade; termo alternativo para produto compatível; produto acima do teto; busca sem resultado; falha recuperável do catálogo. Um agente fixture produz intenções determinísticas e um writer MCP simulado persiste somente em memória. A avaliação mede o contrato da API e as validações do backend; não mede a seleção do agente local real, a interpretação de termos pelo modelo nem a qualidade geral de suas respostas.

| Cenário | Pedido | Fixture e regra esperada |
|---|---|---|
| Teto e quantidade | 2 notebooks até US$ 1.500 cada | Notebook de US$ 1.250; validar categoria, teto, quantidade 2 e total recalculado. |
| Termo alternativo | computador portátil abaixo de US$ 1.500 | A fixture associa o termo à categoria `laptops`; validar compatibilidade e preço dentro do teto. |
| Acima do teto | 1 notebook até US$ 1.500 | Produto de US$ 2.400; esperar `no_compatible_product` sem gravação. |
| Sem resultado | produto inexistente | Agente fixture sem candidatos; esperar `no_compatible_product` sem gravação. |
| Falha recuperável | 1 monitor | Catálogo fixture indisponível; esperar `catalog_unavailable` sem gravação. |

## Arquitetura

```mermaid
flowchart LR
  Browser[Chat React] -->|HTTP| API[Backend FastAPI]
  API -->|MCP autenticado| MCP[Servidor MCP]
  MCP -->|HTTPS| Catalog[DummyJSON]
  MCP -->|SQL: gravação| DB[(PostgreSQL)]
  API -->|SQL: leitura| DB
  API -. opcional .-> LLM[OpenAI ou OpenRouter]
```

O servidor MCP é acessível ao backend pela rede privada do Compose e exige token de serviço. O navegador conversa apenas com o frontend e a API. O modelo recebe ferramentas de busca e, após obter candidatos, pode emitir uma intenção de criação; o backend intercepta e valida essa intenção antes de encaminhar o comando ao MCP. OpenAI e OpenRouter são opcionais e só participam quando configurados explicitamente. A migração roda em serviço separado, e sua credencial de proprietário não é fornecida aos processos de runtime.

## Estrutura do repositório

### Código e ambiente

| Caminho | Conteúdo |
|---|---|
| `compose.yaml` | Serviços, rede, dependências saudáveis, variáveis, healthchecks e volume do PostgreSQL. |
| `.env.example` | Modelo de configuração local, sem credenciais utilizáveis. Copie para `.env`. |
| `.gitignore` | Exclui o PDF do case e arquivos `.env` locais; permite versionar `.env.example`. |
| `.github/workflows/ci.yml` | Pipeline de frontend, backend, MCP, avaliação e validação de configuração, sem deploy. |
| `scripts/check_secrets.py` | Verificação local e na CI de arquivos sensíveis e padrões de credenciais, sem imprimir seus valores. |
| `backend/Dockerfile` | Imagem Python do backend e comando de inicialização FastAPI. |
| `backend/requirements.txt` | Dependências Python do backend e seus testes. |
| `backend/app/main.py` | API, contexto por execução, validação de proveniência/preços, comando canônico de escrita e listagem somente de leitura. |
| `backend/app/migrate.py` | Migração compatível do schema e preflight transacional das roles e permissões do banco. |
| `backend/app/mcp_client.py` | Cliente MCP autenticado, allowlist de catálogo e método específico de persistência. |
| `backend/app/agent.py` | Adaptadores local, OpenAI e OpenRouter; loop limitado de ferramentas e intenção de criar requisição. |
| `backend/tests/test_requisicoes.py` | Integração da API, telemetria, incompatibilidade e falhas, usando banco exclusivo de teste. |
| `backend/tests/test_mcp_write_contract.py` | Proveniência, limites, reconstrução de valores e fronteira entre intenção do modelo e comando MCP. |
| `backend/tests/test_migration_grants.py` | Grants efetivos, roles preexistentes, rollback de migração e integridade de linhas no PostgreSQL de teste. |
| `backend/tests/test_evaluation.py` | Verifica que os cinco cenários controlados passam e produzem os mesmos resultados em execuções repetidas. |
| `backend/evaluation/run.py` | CLI dos cinco cenários: usa a API FastAPI, fixtures de agente/catálogo e banco em memória isolado. |
| `backend/evaluation/__init__.py` | Marca a avaliação como pacote Python executável com `python -m evaluation.run`. |
| `mcp-server/Dockerfile` | Imagem Python do servidor de ferramentas MCP. |
| `mcp-server/requirements.txt` | Dependências do servidor MCP e testes. |
| `mcp-server/app/main.py` | Tools de busca, detalhe e gravação autenticada e idempotente. |
| `mcp-server/app/__init__.py` | Marca o diretório da aplicação como pacote Python. |
| `mcp-server/tests/test_catalog_tools.py` | Testes das tools MCP com respostas HTTP simuladas. |
| `mcp-server/tests/test_requisition_persistence.py` | Autenticação HTTP, sanitização, normalização, escrita, idempotência concorrente e rollback. |
| `frontend/Dockerfile` | Imagem Node para servir a aplicação React durante desenvolvimento local. |
| `frontend/package.json` | Metadados e dependências/scripts do frontend. |
| `frontend/package-lock.json` | Versões resolvidas usadas por `npm ci` para instalações reproduzíveis. |
| `frontend/biome.json` | Regras de lint do código React. |
| `frontend/vite.config.js` | Configuração do Vite e plugin React. |
| `frontend/index.html` / `frontend/src/main.jsx` | Documento HTML e ponto de entrada da aplicação React. |
| `frontend/src/App.jsx` / `frontend/src/styles.css` | Formulário, resultado, ferramentas executadas, histórico e estilos responsivos. |
| `frontend/src/App.test.jsx` | Testes da telemetria na interface e da limpeza entre envios e falhas. |

### Documentação de produto, arquitetura e design

| Caminho | Conteúdo |
|---|---|
| `docs/PRD.md` | Problema, público, requisitos, histórias e critérios de sucesso do MVP. |
| `docs/architecture/STACK.md` | Tecnologias, topologia local, configuração e trade-offs. |
| `docs/architecture/AGENTE-COMPRAS-ARCH.md` | Entidades, contrato HTTP/MCP, ciclo do agente, validações e falhas. |
| `docs/architecture/OPCIONAIS-ARCH.md` | Contratos do Ciclo 04, MCP writer, idempotência, limites e risco residual da demonstração. |
| `docs/architecture/AVALIACAO-LLM-ARCH.md` | Arquitetura planejada para avaliação manual opt-in com LLM, fixtures e teto de custo. |
| `docs/designs/DESIGN.md` | Direção visual, tokens, layout, estados, responsividade e acessibilidade. |

### Planejamento SDD e histórico de entrega

| Caminho | Conteúdo |
|---|---|
| `CICLO-01-FUNDACAO-MCP-Tasks.md` | Índice do ciclo de Compose, servidor MCP e testes. |
| `CICLO-02-BACKEND-AGENTE-Tasks.md` | Índice do ciclo de persistência, agente e API. |
| `CICLO-03-ENTREGA-Tasks.md` | Índice do ciclo de interface, README, testes e revisão final. |
| `CICLO-04-DIFERENCIAIS-Tasks.md` | Planejamento dos opcionais: telemetria de tools no chat, script de avaliação, CI e tool de gravação MCP. |
| `docs/stories/ciclo-05-avaliacao-llm/01-avaliacao-agente-real.story.md` | Story planejada para medir cinco decisões do agente real, sem escrita no banco demonstrativo. |
| `docs/stories/ciclo-01-fundacao-mcp/` | Stories e logs de execução da fundação e do servidor MCP. |
| `docs/stories/ciclo-02-backend-agente/` | Stories e logs de execução do banco, agente e API. |
| `docs/stories/ciclo-03-entrega/` | Stories e logs de execução da interface e preparação da entrega. |
| `docs/stories/ciclo-04-diferenciais/` | Quatro stories detalhadas dos diferenciais opcionais; a tool de gravação tem gate arquitetural e de segurança antes da implementação. |

Os logs das stories registram o que mudou, decisões tomadas e evidências de validação. O Git complementa esses registros com commits pequenos e mensagens descritivas.

## SDD aplicado neste projeto

SDD significa **Specification-Driven Development**: primeiro registramos o que construir e por quê; depois detalhamos como as partes se conectam; então planejamos o trabalho em ciclos aprovados, implementamos e validamos cada entrega. Neste repositório, o fluxo está materializado em:

1. PRD de produto com problema, requisitos e critérios de sucesso.
2. Especificação de arquitetura com contratos, dados, erros e limites.
3. Especificação visual antes da interface.
4. Stories pequenas com dependências, critérios verificáveis e logs.
5. Implementação em commits rastreáveis, seguida por testes e revisão.

Ferramentas de IA apoiaram planejamento, implementação e revisão sob supervisão humana; os documentos, testes e commits registram as decisões e resultados verificáveis.

### Como usei IA e subagentes

Usei o Codex para apoiar a construção do projeto, com subagentes especializados e revisão humana. Os nomes identificam papéis de trabalho, não serviços necessários para rodar a aplicação:

| Papel | Contribuição no desenvolvimento |
|---|---|
| Iroh | Coordenação e comunicação das decisões e próximos passos. |
| Senku | Arquitetura, contratos e análise de trade-offs. |
| Levi | Organização das stories, dependências e gates de entrega. |
| Gohan | Implementação do backend e da integração MCP. |
| Vegeta | Implementação da interface React. |
| Itachi | Ambiente de execução e infraestrutura. |
| Jin-Woo | Revisão de persistência e permissões do banco. |
| Gojo | Revisão de segurança. |
| Tanjiro | Testes e verificação dos critérios de aceite. |

Os subagentes foram usados durante o desenvolvimento; o agente de compras é uma parte separada da aplicação. As decisões, limitações e evidências estão nos documentos e testes do repositório.

## Ciclo 04: diferenciais

O planejamento e as evidências estão em [`CICLO-04-DIFERENCIAIS-Tasks.md`](CICLO-04-DIFERENCIAIS-Tasks.md) e nas stories de `docs/stories/ciclo-04-diferenciais/`:

| Opcional | Estado documentado | Entrega |
|---|---|---|
| 1. Ferramentas no chat | Done | Exibe somente os nomes das tools executadas naquela requisição e limpa o estado entre envios. |
| 2. Avaliação com cinco pedidos | Done | CLI determinístico com relatório `N/5`, fixtures isoladas e código de saída verificável. |
| 3. CI de lint e testes | Done | Workflow executado no GitHub para o commit de entrega; jobs Python, frontend e configuration concluíram com sucesso. |
| 4. Tool `criar_requisicao` | Done para demonstração local | MCP writer autenticado, idempotência e roles separadas; risco residual documentado. Testes de logs cobrem INFO, não DEBUG do SDK MCP. |

## Ciclo 05: avaliação do agente real

O modo opt-in executou cinco pedidos sintéticos com o modelo `gpt-5.4-nano` e fixtures de catálogo e persistência em memória. Resultado: **5/5**, 13 chamadas, 5.346 tokens de entrada, 456 de saída e custo estimado de **US$ 0,00205**, incluindo margem de 25%. O teto da reserva estimada é US$ 0,50; a cobrança efetiva pode divergir. A suíte completa do backend passou com **40 testes**; os testes do servidor MCP passaram com **20 testes**. Uma validação de integração entre backend, catálogo DummyJSON, tools MCP e PostgreSQL descartável confirmou criação e listagem da requisição. O fluxo completo em navegador ainda não foi validado; veja [`04-testes-e2e.story.md`](docs/stories/ciclo-03-entrega/04-testes-e2e.story.md). A CI do commit `849c009` passou nos três jobs. A avaliação live continua fora da CI; os testes reportaram avisos de depreciação em dependências. Consulte [`AVALIACAO-LLM-ARCH.md`](docs/architecture/AVALIACAO-LLM-ARCH.md), o [planejamento do Ciclo 05](CICLO-05-AVALIACAO-LLM-Tasks.md) e a [story](docs/stories/ciclo-05-avaliacao-llm/01-avaliacao-agente-real.story.md).

## API principal

### `POST /requisicoes`

```json
{
  "pedido": "Preciso de 3 laptops para o time de vendas, até US$ 2.000 cada."
}
```

Em sucesso, retorna `201` com número da requisição, itens, preço unitário, total, justificativa e `ferramentasChamadas`. Erros seguem o formato `{"erro":{"codigo":"...","mensagem":"..."}}`.

### `GET /requisicoes`

Retorna as requisições salvas em ordem decrescente de criação.

## Limites conhecidos

- O modo local usa regras determinísticas simples para permitir desenvolvimento sem provedor de LLM.
- O catálogo DummyJSON é dado de demonstração, não estoque ou preço comercial garantido.
- Não há login, aprovação, ERP, pagamento ou disponibilidade real de produtos.
- A demonstração pressupõe um cluster PostgreSQL dedicado, sem dados de outros projetos. O Compose mantém PostgreSQL e MCP sem portas publicadas no host.
- A role do MCP tem `SELECT` e `INSERT` nas tabelas de requisições e itens. Se o processo MCP ou sua credencial forem comprometidos, esses privilégios permitem fabricar requisições ou anexar itens a um cabeçalho existente. Esse risco médio foi aceito para o case local e está detalhado em `docs/architecture/OPCIONAIS-ARCH.md`. Para produção, a evolução recomendada é uma função SQL `SECURITY DEFINER` estreita com permissão somente de `EXECUTE`, `search_path` fixo e proprietário `NOLOGIN`, ou controle equivalente.
