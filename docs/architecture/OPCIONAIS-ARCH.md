# ARCH — Diferenciais opcionais

## 1. Escopo e sequência

Este documento especifica os quatro opcionais do Ciclo 04. As Stories 1–3 acrescentam observabilidade, avaliação repetível e validação contínua sem alterar a regra de compra. A Story 4 altera a fronteira de persistência e deve permanecer bloqueada até aprovação desta especificação e da revisão de segurança.

| Story | Responsabilidade técnica | Risco |
|---|---|---|
| 1. Tools no chat | Correlacionar chamadas MCP de uma execução e retornar só seus nomes | Baixo |
| 2. Avaliação de cinco pedidos | Cenários determinísticos, isolados do banco de demonstração e das APIs pagas | Médio |
| 3. CI | Reproduzir build, lint e testes sem segredos nem rede de modelo | Baixo |
| 4. `criar_requisicao` | Modelo inicia a intenção de gravar; backend valida; MCP executa comando de persistência idempotente | Alto |

## 2. Story 1 — telemetria MCP

O backend já intercepta chamadas MCP por execução em `ExecutionCatalog`. Esse é o ponto único para registrar eventos; a UI não infere tools a partir do tipo de produto ou do modo do agente.

Contrato de sucesso aditivo para `POST /requisicoes`:

```json
{
  "requisicao": {
    "numero": 12,
    "itens": [],
    "valorTotal": 5999.97,
    "ferramentasChamadas": ["buscar_produtos", "detalhar_produto"]
  }
}
```

Regras:

- A lista é criada por requisição, deduplicada mantendo a ordem da primeira chamada e preenchida pelo backend.
- Incluir apenas tools MCP allowlisted efetivamente despachadas. Uma chamada inválida pode ser mostrada como tentativa somente se isso for explicitamente rotulado; por padrão, retornar apenas tools executadas com sucesso.
- Não retornar argumentos, conteúdo do catálogo, prompts, IDs de sessão MCP, headers ou credenciais.
- Em falha HTTP, não apresentar telemetria de uma solicitação anterior. Em erros, o contrato atual de erro permanece estável.
- O frontend rotula os nomes como atividade do catálogo; não deve dizer que a tool criou algo até a Story 4 existir.

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

Pipeline recomendado em GitHub Actions para pull requests e push em `main`, com jobs independentes:

1. Frontend: `npm ci`, lint e `npm run build`.
2. Python: instalação com versões fixadas, lint Python e testes de backend/MCP.
3. Compose: `docker compose config` com valores dummy injetados pelo job; não iniciar serviços nem enviar credenciais.
4. Segredos: scanner para diff/histórico recente ou ação equivalente configurada com versão/pin imutável.

Não usar `OPENAI_API_KEY`, `OPENROUTER_API_KEY` nem executar cenário cobrável na CI. O script de avaliação roda no modo fixture. Pins e lockfiles devem tornar `npm ci` e instalação Python repetíveis. Primeiro tornar explícitos os comandos de lint e suas configurações, pois o frontend hoje tem build mas não possui script de lint declarado.

## 5. Story 4 — `criar_requisicao`

### Decisão recomendada

O LLM escolhe se e quando invocar `criar_requisicao`. O modelo não é autoridade para validar preços, origem de produto, totais ou persistência. A API/backend permanece autoridade de negócio e valida cada chamada; o servidor MCP executa o comando de gravação numa transação Postgres e aplica constraints. O banco não é acessível pelo frontend.

Fluxo:

```text
LLM escolhe tools de catálogo
  → backend executa tools MCP e registra IDs/atributos em ExecutionCatalog desta requisição
  → LLM pode chamar criar_requisicao com IDs e quantidades
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
- Quantidade inteira positiva, dentro de limite máximo configurado para evitar abuso/custo de demonstração.
- Todos os itens pertencem ao pedido/execution context atual; rejeitar referências de execução anterior.
- Reconsultar `detalhar_produto` para cada ID e usar preço/título atuais do catálogo; aplicar o teto unitário do pedido.
- Calcular `valor_total` e `valor_total` da requisição com `Decimal`; rejeitar lista vazia, item repetido ambíguo ou valor que exceda precisão/limites do schema.
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

O servidor MCP valida schema e consistência aritmética novamente como defesa em profundidade. O total deve igualar a soma dos itens. Resposta inclui `id`, `numero`, `criada_em`, total e itens persistidos; não devolve credenciais nem permite escrita arbitrária por SQL/payload livre.

### Idempotência e transação

- Backend cria UUID de idempotência uma vez por execução lógica e reutiliza em retries de transporte da mesma tool call.
- Adicionar coluna única `chave_idempotencia` a `requisicoes` com migração idempotente. Reuso da mesma chave e mesmo payload devolve a requisição existente; mesma chave com payload diferente retorna conflito estável.
- Uma transação Postgres grava cabeçalho e todos os itens; qualquer falha causa rollback total.
- Tool call do LLM repetida com mesma chave não cria duplicata. Timeout após commit seguido de retry retorna o registro já criado.
- O backend mantém o resultado da tool em memória para não chamar gravação outra vez ao continuar o diálogo do modelo. Depois de uma criação, chamadas subsequentes `criar_requisicao` na mesma execução são rejeitadas ou retornam a mesma resposta idempotente.

### Limites e falhas

- A tool de gravação só é oferecida ao modelo após haver candidatos buscados e validação suficiente para permitir um pedido válido.
- Limite global atual de seis tool calls inclui busca, detalhe e gravação; timeout total permanece 15 s.
- MCP retorna erro de domínio sem stack trace. O backend traduz para os códigos existentes (`agent_result_invalid`, `no_compatible_product`, `catalog_unavailable`) e acrescenta `persistence_unavailable`/503 para falha de escrita.
- O backend não pode executar uma segunda gravação fallback direta depois de erro da tool; isso tornaria a intenção do modelo sem efeito e introduziria dupla autoridade.
- Só chamar o POST final de sucesso depois de receber confirmação persistida do MCP.

### Decisões necessárias antes da implementação

1. Confirmar se o MCP server recebe `DATABASE_URL` de escrita e se essa responsabilidade de persistência é aceitável. Alternativa é mover MCP para o mesmo processo do backend, o que altera topologia e reduz isolamento.
2. Confirmar compatibilidade da migração e da chave de idempotência com bancos existentes do case.
3. Definir limite máximo por quantidade e número de itens.
4. Gojo deve revisar o contrato, credencial de banco do MCP e proteção contra replay antes de execução.

## 6. Gate técnico para Levi

- Stories 1–3 podem ser aprovadas para execução após o índice/stories refletirem os contratos acima.
- Story 4 deve permanecer Draft/Blocked for Architecture até que o usuário aprove a responsabilidade de escrita MCP, os limites e a estratégia de idempotência; depois disso Gojo revisa antes da implementação.
- Não considerar o Ciclo 04 concluído só pelo CI verde: a demonstração do quinto caso e, se implementada, da persistência MCP precisam ser reproduzíveis no README.
