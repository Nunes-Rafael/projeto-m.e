# ARCH — Diferenciais opcionais

## 1. Escopo e sequência

Este documento especifica os quatro opcionais do Ciclo 04. As Stories 1–3 acrescentam observabilidade, avaliação repetível e validação contínua sem alterar a regra de compra. A Story 4 foi aprovada para a demonstração local por Senku, Jin-Woo, Gojo e Tanjiro, com risco residual explícito neste ARCH e na story.

| Story | Responsabilidade técnica | Risco |
|---|---|---|
| 1. Tools no chat | Correlacionar chamadas MCP de uma execução e retornar só seus nomes | Baixo |
| 2. Avaliação de cinco pedidos | Cenários determinísticos, isolados do banco de demonstração e das APIs pagas | Médio |
| 3. CI | Reproduzir build, lint e testes sem segredos nem rede de modelo | Baixo |
| 4. `criar_requisicao` | Modelo inicia a intenção de gravar; backend valida; MCP executa comando de persistência idempotente | Alto |

**Decisão aprovada por Rafael:** o servidor MCP poderá receber credencial de escrita no Postgres exclusivamente para executar `criar_requisicao`. O acesso deve ser limitado ao banco/schema e às operações necessárias, mantido em segredo de ambiente e nunca exposto ao modelo ou frontend. A topologia de escrita via MCP fica aprovada; permanecem os controles técnicos e a revisão de segurança descritos abaixo.

## 2. Story 1 — telemetria MCP

O backend já intercepta chamadas MCP por execução em `ExecutionCatalog`. Esse é o ponto único para registrar eventos; a UI não infere tools a partir do tipo de produto ou do modo do agente.

Contrato de sucesso aditivo para `POST /requisicoes`:

```json
{
  "requisicao": {
    "numero": 12,
    "itens": [],
    "valorTotal": 5999.97,
    "ferramentasChamadas": ["buscar_produtos", "detalhar_produto", "criar_requisicao"]
  }
}
```

Regras:

- A lista é criada por requisição, deduplicada mantendo a ordem da primeira chamada e preenchida pelo backend.
- Incluir apenas tools MCP allowlisted efetivamente executadas nesta requisição. `criar_requisicao` aparece apenas depois de confirmação de persistência pelo MCP. Uma chamada inválida pode ser mostrada como tentativa somente se isso for explicitamente rotulado; por padrão, retornar apenas tools executadas com sucesso.
- Não retornar argumentos, payloads de entrada ou saída, conteúdo do catálogo, prompts, IDs de sessão MCP, headers ou credenciais.
- Em falha HTTP, não apresentar telemetria de uma solicitação anterior. Em erros, o contrato atual de erro permanece estável.
- O frontend usa o rótulo genérico “Ferramentas MCP executadas”, pois a lista inclui busca, detalhe e a tool de persistência quando confirmada.

Verificação: testes backend para busca, busca+detalhe, tool recusada e falha; teste React confirma renderização da lista e ausência de dados de argumentos.

## 3. Story 2 — script de avaliação

O script deve medir critérios determinísticos do comportamento e executar contra dependências controladas. Não chamar OpenAI, OpenRouter ou DummyJSON real. Não usar o banco persistente de demonstração.

### Cenários propostos

| Caso | Pedido/estímulo controlado | Critério de aprovação |
|---|---|---|
| 1. Seleção compatível | 3 laptops, teto unitário US$ 2.000 | 201; quantidade 3; preço unitário ≤ teto; total = quantidade × unitário; linha visível na lista |
| 2. Produto fora do teto | Busca mock retorna opção acima do limite | `no_compatible_product`; nenhuma linha nova |
| 3. Busca vazia | Busca mock retorna zero produtos | `no_compatible_product`; nenhuma linha nova |
| 4. Falha de catálogo | MCP mock retorna timeout/indisponível | `catalog_unavailable`; nenhuma linha nova |
| 5. Resultado inconsistente | Agente controlado aponta ID inexistente/não proveniente da busca | `agent_result_invalid`; nenhuma linha nova |

Critérios devem testar status, códigos estáveis, quantidades, preços, totais, tools e efeito no banco; não igualdade de texto ou escolha exata de produto em catálogo não determinístico. O script pode usar o ASGI TestClient/fixtures do backend e mocks HTTP para MCP e catálogo, evitando subir Docker para cada cenário. O output esperado é por caso `PASS`/`FAIL`, resumo `N/5` e exit code zero somente quando todos passam. Os fixtures precisam ser isolados e o script não pode emitir uma requisição real ao modelo.

## 4. Story 3 — CI

Pipeline implementado em `.github/workflows/ci.yml` para pull requests e push em `main`, com jobs independentes:

1. Frontend: `npm ci`, lint e `npm run build`.
2. Python: instalação com versões fixadas, testes de backend/MCP e avaliação determinística.
3. Compose: `docker compose config` com valores dummy injetados pelo job; não iniciar serviços nem enviar credenciais.
4. Segredos: scanner local de nomes sensíveis e padrões conhecidos de credenciais.

Não usar `OPENAI_API_KEY`, `OPENROUTER_API_KEY` nem executar cenário cobrável na CI. O script de avaliação roda no modo fixture. Pins e lockfiles tornam `npm ci` e a instalação Python repetíveis. O lint Biome do frontend termina sem erro e emite avisos conhecidos de configuração CSS; backend e MCP são cobertos por testes.

## 5. Story 4 — `criar_requisicao`

### Decisão recomendada

O LLM pode propor a intenção de invocar `criar_requisicao`, mas não recebe conexão MCP direta nem uma credencial/tool de escrita utilizável fora do backend. O backend intercepta essa intenção, verifica allowlist e payload, valida preços, origem de produto, totais e política da requisição. Só então o backend chama a operação MCP interna autenticada; o servidor MCP valida novamente o contrato e grava numa transação Postgres. O banco não é acessível pelo frontend.

Fluxo:

```text
LLM escolhe tools de catálogo
  → backend executa tools MCP e registra IDs/atributos em ExecutionCatalog desta requisição
  → LLM emite intenção criar_requisicao com IDs e quantidades, sem acesso MCP direto
  → backend intercepta e valida allowlist, proveniência, teto e quantidades
  → backend detalha novamente os produtos via MCP e monta snapshot canônico
  → backend chama MCP criar_requisicao com snapshot canônico + chave idempotente
  → servidor MCP grava requisição e itens atomicamente no Postgres
  → resultado retorna ao backend e à resposta HTTP
```

Essa composição mantém a decisão de gravar no LLM, mas impede que dados financeiros enviados pelo modelo sejam aceitos como verdade. Nenhum campo de preço, total, título ou justificativa enviado pelo modelo deve ser persistido diretamente.

### Entrada solicitada pelo modelo

```json
{
  "itens": [
    { "produto_id": 78, "quantidade": 3 }
  ]
}
```

Validações no backend antes de chamar a tool de gravação:

- `produto_id` inteiro positivo e presente no conjunto de IDs retornados por `buscar_produtos` nesta mesma execução.
- Quantidade inteira de 1 a 100 por item.
- Todos os itens pertencem ao pedido/execution context atual; rejeitar referências de execução anterior.
- Reconsultar `detalhar_produto` para cada ID e usar preço/título atuais do catálogo; aplicar o teto unitário do pedido.
- Aceitar no máximo 20 itens distintos por requisição e quantidade de 1 a 100 por item. Esses limites são de domínio para o case, além do limite de preço e da precisão `NUMERIC(12, 2)` já adotada pelo schema. Rejeitar lista vazia, IDs repetidos (o backend não deve agregar silenciosamente), quantidades fracionárias/não inteiras e totais fora da faixa representável.
- Calcular cada total de linha e o total da requisição com `Decimal` quantizado a duas casas; nunca usar `float` para cálculo financeiro.
- Se não houver compatibilidade, não oferecer/aceitar a tool de gravação e retornar `no_compatible_product`.

### Payload canônico backend → MCP

O backend chama `criar_requisicao` com dados já reconstruídos e validados:

```json
{
  "chave_idempotencia": "<uuid criado pelo backend para esta execução>",
  "pedido_original": "…",
  "itens": [
    {
      "produto_origem_id": 78,
      "titulo": "Apple MacBook Pro 14 Inch Space Grey",
      "quantidade": 3,
      "preco_unitario": "1999.99",
      "valor_total": "5999.97"
    }
  ],
  "valor_total": "5999.97"
}
```

O servidor MCP valida schema, limites máximos (20 linhas, quantidade 1–100) e consistência aritmética novamente como defesa em profundidade. O total deve igualar a soma dos itens e cada total de linha deve igualar quantidade × preço unitário, com precisão de centavos. A validação de negócio e a prova de proveniência continuam sendo responsabilidade do backend; o MCP aceita apenas o contrato canônico e não oferece ferramenta de escrita diretamente ao modelo.

### Controles verificáveis de serviço e banco

- **Autenticação backend→MCP:** usar segredo de serviço dedicado, injetado por ambiente/secrets e enviado em header de autenticação. O MCP compara o segredo em tempo constante com valor configurado; segredo ausente, vazio ou inválido rejeita a chamada antes de qualquer acesso ao banco. Não há modo permissivo nem fallback sem autenticação. O segredo não pode aparecer em resposta, exceção ou log.
- **Autorização de rede:** o endpoint MCP de escrita não pode ser publicado no host. Backend e MCP usam uma rede Compose dedicada à comunicação entre serviços, mas a rede compartilhada, sozinha, não é controle de autorização: autenticação de aplicação é obrigatória em cada chamada. Apenas o backend deve ter rota de saída para o endpoint de escrita; nenhuma rota pública ou do frontend expõe essa tool.
- **Privilégios PostgreSQL:** runtime do MCP conecta como role não proprietário, sem `SUPERUSER`, `CREATEDB`, `CREATEROLE`, ownership de schema/tabelas ou privilégios amplos. Conceder somente `CONNECT` no database, `USAGE` no schema e operações estritamente necessárias nas tabelas/sequence de requisição. Migrações usam credencial separada de owner, indisponível no runtime. Validar grants efetivos na revisão.
- **Teste de fail-closed:** integração MCP sem header, com segredo incorreto e com segredo correto; os dois primeiros devem resultar em rejeição e zero linhas novas. Configuração sem segredo deve impedir o MCP de iniciar ou de habilitar a tool de gravação.

### Idempotência e transação

- Backend cria UUID de idempotência uma vez por execução lógica e reutiliza em retries de transporte da mesma operação de gravação. Antes de persistir, normaliza o payload canônico (campos permitidos, ordem determinística dos itens, strings decimais em duas casas e representação estável). O MCP aplica a mesma normalização e calcula o hash criptográfico; não confia em hash fornecido pelo modelo nem aceita payload/hash fora do contrato. A chave não vem do modelo.
- Adicionar coluna única `chave_idempotencia` e hash do payload normalizado a `requisicoes`, com migração idempotente. Registros históricos podem continuar sem chave/hash; toda nova gravação exige ambos. O MCP impõe unicidade da chave no banco. Para chamadas concorrentes, a primeira transação que reserva a chave grava; chamadas com a mesma chave aguardam/consultam o resultado confirmado. Mesmo hash devolve a mesma linha persistida; hash diferente retorna conflito estável. A decisão ocorre no servidor/banco com constraint e transação, sem janela check-then-insert; conflito nunca deixa cabeçalho ou itens parciais.
- Uma transação Postgres grava cabeçalho e todos os itens; qualquer falha causa rollback total. Os itens são inseridos apenas após a reserva idempotente; commit torna cabeçalho e itens visíveis juntos.
- Tool call do LLM repetida não cria nova operação lógica: o backend mantém a primeira intenção validada e associa a ela a mesma chave, sem deixar o modelo escolher ou alterar a chave. Timeout após commit seguido de retry pelo backend retorna o registro já criado.
- O backend mantém o resultado da tool em memória para não chamar gravação outra vez ao continuar o diálogo do modelo. Depois de uma criação, chamadas subsequentes `criar_requisicao` na mesma execução são rejeitadas ou retornam a mesma resposta idempotente.

### Limites e falhas

- A tool de gravação só é oferecida ao modelo após haver candidatos buscados e validação suficiente para permitir um pedido válido.
- Limite global atual de seis tool calls inclui busca, detalhe e gravação; timeout total permanece 15 s.
- MCP retorna erro de domínio sem stack trace. O backend traduz para os códigos existentes (`agent_result_invalid`, `no_compatible_product`, `catalog_unavailable`) e acrescenta `persistence_unavailable`/503 para falha de escrita.
- Logs estruturados registram correlation ID, nome da tool, resultado/código e duração, mas não incluem segredo, header de autenticação, prompt, payload completo, nomes de produto ou dados financeiros. Exceções internas e SQLSTATE ficam nos logs restritos somente se sanitizados; respostas públicas contêm códigos estáveis e mensagem sem detalhes internos.
- O backend não pode executar uma segunda gravação fallback direta depois de erro da tool; isso tornaria a intenção do modelo sem efeito e introduziria dupla autoridade.
- Só chamar o POST final de sucesso depois de receber confirmação persistida do MCP.

### Gates e risco residual aceito

| Gate | Status |
|---|---|
| Senku — arquitetura | Aprovado: fronteiras, payload canônico, idempotência e limites definidos neste documento. |
| Jin-Woo — dados | Sign-off concedido para os dados do case, incluindo schema e integridade relacional. |
| Gojo — segurança | Sign-off condicional concedido; o risco residual e os controles estão documentados neste ARCH e na Story. |

Decisões de arquitetura e controles verificados: MCP recebe credencial de escrita no Postgres; migração adiciona chave de idempotência única para novas gravações, permitindo registros históricos sem chave; limites são até 20 itens distintos, quantidade inteira de 1 a 100 por item, pedido de até 2.000 caracteres e valores compatíveis com `NUMERIC(12, 2)`. Autenticação, rede, grants, idempotência, transação e sanitização foram validados por testes isolados descritos na Story 4.

**Risco residual aceito somente para a demonstração local:** o role runtime do MCP terá `SELECT` e `INSERT` nas tabelas `requisicoes` e `itens_requisicao` para executar o fluxo. Se o processo MCP ou sua credencial forem comprometidos, um atacante pode inserir requisições fabricadas e inserir um item apontando para um cabeçalho existente. O role não terá `UPDATE`, `DELETE`, DDL, ownership, `SUPERUSER`, `CREATEDB` ou `CREATEROLE`. Este risco é médio e está fora do escopo de produção.

Premissa de isolamento: o Postgres usado no case/demonstração está em cluster dedicado, sem bancos de outros projetos ou dados não relacionados. Como `PUBLIC` pode ter `CONNECT` no database por padrão, esse privilégio deve ser revogado quando aplicável e o acesso concedido explicitamente às roles necessárias. O Compose não publica a porta do Postgres no host; somente os serviços internos necessários acessam a rede privada. A rede do Compose não substitui a autenticação backend→MCP.

Para produção ou least privilege estrito, preferir uma função `SECURITY DEFINER` estreita, executável apenas pelo role runtime (`EXECUTE`-only), com `search_path` fixo e owner `NOLOGIN`, ou mecanismo equivalente que limite o MCP à operação atômica de criar requisição. Isso reduz privilégios de tabela, mas duplica invariantes e lógica no banco; manter a validação canônica no backend e as constraints/transação no banco exige revisão cuidadosa para evitar divergência.

Critérios verificáveis cobertos pelos sign-offs: chamadas não autenticadas falham antes de SQL; MCP não é publicado no host e rede privada não substitui autenticação; grants do role runtime excluem ownership/privilégios administrativos e se limitam a `SELECT`/`INSERT` nas duas tabelas; modelo não consegue chamar MCP diretamente e backend rejeita IDs sem proveniência ou payload financeiro fornecido pelo modelo; chamadas concorrentes com mesma chave+payload devolvem a mesma requisição e mesma chave+payload diferente produzem conflito sem linhas parciais; falha em inserir qualquer item reverte cabeçalho e itens; logs/erros não expõem segredos ou conteúdo sensível nos testes executados em nível INFO. O nível DEBUG do SDK MCP não foi coberto.

## 6. Gate técnico para Levi

- Stories 1–4 foram aprovadas para execução e concluídas conforme os critérios locais; a Story 3 permanece em Review até uma execução do workflow no GitHub.
- Story 4 foi marcada Done para a demonstração local após os sign-offs de Senku, Jin-Woo e Gojo e a aprovação de QA de Tanjiro. O risco residual é aceito somente para esse escopo; a decisão não certifica uso em produção. A implementação não reabre as decisões de topologia, limites ou idempotência documentadas acima.
- Não considerar o Ciclo 04 concluído só pelo CI verde: a demonstração do quinto caso e a persistência MCP devem permanecer reproduzíveis no README e nos testes locais.
