# ARCH — Agente de Compras

## 1. Visão técnica

O backend recebe um pedido textual e conduz um ciclo limitado de tool-calling. Em modo `openrouter`, o modelo recebe o pedido, as definições de ferramentas e as respostas dessas ferramentas. Ele decide se precisa buscar produtos, detalhar um produto ou encerrar a análise. O código não programa uma sequência fixa de chamadas.

O backend, porém, continua sendo a autoridade para segurança e persistência: valida a chamada de ferramenta, aplica timeout, confere o resultado final contra os dados retornados pelo catálogo, recalcula valores e só então abre uma transação no banco.

Em modo `local`, um adaptador determinístico serve exclusivamente ao desenvolvimento sem chave: exercita as mesmas interfaces com respostas controladas. Ele deve ser identificado no README e na interface de diagnóstico como modo de desenvolvimento; não é evidência de que o requisito de decisão pelo LLM foi atendido.

## 2. Componentes e responsabilidades

| Componente | Responsabilidade | Não faz |
|---|---|---|
| Frontend | Coleta o texto, exibe carregamento, sucesso e erro compreensível | Não seleciona produtos nem calcula preço final. |
| Backend | API, loop do agente, validação, transação e mapeamento de erros | Não chama DummyJSON diretamente. |
| Servidor MCP | Implementa ferramentas, normaliza respostas DummyJSON e controla timeout externo | Não persiste requisições nem usa LLM. |
| Postgres | Persiste requisições e snapshot dos itens escolhidos | Não é exposto ao browser. |

## 3. Contrato MCP

### `buscar_produtos`

Entrada:

```json
{ "termo": "laptop" }
```

Saída normalizada:

```json
{
  "produtos": [
    { "id": 1, "titulo": "…", "preco": 999.99, "categoria": "…", "marca": "…" }
  ]
}
```

Regras: `termo` é obrigatório, após trim tem entre 2 e 120 caracteres. A ferramenta consulta `GET /products/search?q=` na DummyJSON. Uma lista vazia é resultado válido, não erro.

### `detalhar_produto`

Entrada:

```json
{ "id": 1 }
```

Saída normalizada: `id`, `titulo`, `preco`, `descricao`, `categoria`, `marca`, `estoque` e demais atributos retornados pelo catálogo que sejam úteis ao modelo. `id` precisa ser inteiro positivo.

Regras comuns: timeout de 3 segundos para a DummyJSON; uma falha de rede, resposta inválida ou HTTP 5xx torna a ferramenta indisponível. A mensagem enviada ao modelo identifica a indisponibilidade sem vazar detalhes internos; o backend a converte em erro claro ao usuário.

## 4. Modelo de dados conceitual

| Entidade | Campos-chave | Relacionamento | Regras |
|---|---|---|---|
| `requisicoes` | `id` UUID, `numero` bigint sequencial, `pedido_original`, `status`, `valor_total`, `criada_em` | Uma requisição possui muitos itens | `numero` é único e é o identificador mostrado no chat; `valor_total` é calculado no servidor. |
| `itens_requisicao` | `id` UUID, `requisicao_id`, `produto_origem_id`, `titulo`, `quantidade`, `preco_unitario`, `valor_total` | Pertence a uma requisição | Snapshot de catálogo; quantidade é inteira positiva; `valor_total = quantidade × preco_unitario`. |

`status` começa restrito a `criada`. Não há estado parcial: em falha de catálogo, validação ou transação, nenhuma linha é persistida. Índices: unicidade em `requisicoes.numero`, índice em `itens_requisicao.requisicao_id` e índice descendente em `requisicoes.criada_em` para a listagem.

## 5. Contrato HTTP

### `POST /requisicoes`

Payload:

```json
{ "pedido": "Preciso de 3 laptops para o time de vendas, até US$ 2.000 cada." }
```

Sucesso — `201 Created`:

```json
{
  "requisicao": {
    "numero": 1,
    "pedido": "…",
    "itens": [
      { "produtoId": 1, "titulo": "…", "quantidade": 3, "precoUnitario": 999.99, "valorTotal": 2999.97 }
    ],
    "valorTotal": 2999.97,
    "justificativa": "…"
  }
}
```

| Condição | Status | Código estável | Regra de interface |
|---|---:|---|---|
| Pedido vazio ou maior que 2.000 caracteres | 422 | `invalid_request` | Mostrar como erro de preenchimento. |
| Pedido ambíguo, sem termo pesquisável ou sem restrição essencial | 422 | `clarification_needed` | Mostrar pergunta ou orientação retornada pelo backend. |
| Catálogo não oferece produto compatível | 422 | `no_compatible_product` | Mostrar requisito que não pôde ser atendido; não há requisição. |
| DummyJSON indisponível ou lenta | 503 | `catalog_unavailable` | Informar falha temporária e permitir nova tentativa. |
| Modo OpenRouter sem configuração, ou falha do provedor | 503 | `agent_unavailable` | Informar indisponibilidade do agente sem detalhes internos. |
| Saída do agente contradiz catálogo ou falha validação | 422 | `agent_result_invalid` | Não persistir; mensagem segura ao usuário. |

Todos os erros seguem:

```json
{ "erro": { "codigo": "catalog_unavailable", "mensagem": "Não foi possível consultar o catálogo agora. Tente novamente." } }
```

### `GET /requisicoes`

Resposta `200 OK`: lista ordenada por criação decrescente, com `numero`, `pedido`, `status`, `valorTotal`, `criadaEm` e resumo de itens. No MVP, o endpoint não pagina porque é destinado à demonstração local; paginação entra antes de uso com volume real.

## 6. Ciclo de decisão do agente

1. Validar o pedido recebido e montar mensagem de sistema que proíbe inventar dados.
2. Oferecer apenas as duas ferramentas MCP e iniciar a primeira chamada ao modelo.
3. Enquanto o modelo solicitar uma ferramenta permitida, validar argumentos, executar a ferramenta via MCP e anexar a resposta à conversa.
4. Encerrar depois de uma resposta final válida ou de no máximo seis chamadas de ferramenta.
5. Validar a estrutura final: produtos devem ter origem no catálogo retornado nesta execução; quantidade é positiva; cada preço respeita o teto extraído; total é recalculado pelo backend.
6. Persistir `requisicoes` e `itens_requisicao` em uma única transação e devolver a resposta.

O modelo não escolhe o que é gravado sem validação. O backend não deve tentar "completar" uma recomendação ausente ou ajustar silenciosamente uma saída inválida.

## 7. Validações e segurança

- Aceitar somente os nomes e schemas das duas ferramentas registradas.
- Tratar resultado do catálogo como dado não confiável; não executar instruções presentes em títulos ou descrições de produto.
- Não incluir chaves, headers de autorização, prompts completos ou stack traces em logs ou respostas HTTP.
- Limitar `pedido` a 2.000 caracteres, limite de seis chamadas de ferramenta e timeout total de 15 segundos por requisição.
- Usar valores monetários decimais no backend e banco, nunca `float` binário; o frontend apenas formata a moeda.
- A migração de banco é idempotente e executa antes de o backend aceitar tráfego.

## 8. Verificação e metas

| Aspecto | Evidência de pronto |
|---|---|
| MCP | Um teste para cada ferramenta com transporte HTTP mockado, sem chave de LLM. |
| Agente real | Com credencial configurada, o caso de laptops mostra ao menos uma chamada de ferramenta e cria requisição válida. |
| Sem compatibilidade | Pedido impossível retorna `no_compatible_product` e não altera banco. |
| Resiliência | Timeout/erro da DummyJSON retorna `catalog_unavailable`; banco não recebe linhas parciais. |
| Persistência | `GET /requisicoes` encontra a requisição criada pelo POST. |
| Compose | `docker compose up --build` deixa os quatro serviços saudáveis e cria o schema sem etapa manual. |
| Tempo | Busca à DummyJSON tem timeout de 3 s; a API responde em até 15 s mesmo em falha externa. |

## 9. Fora do módulo

Autenticação, autorização, aprovação humana, terceiro tool de escrita, ERP, pagamentos, cache, streaming e memória conversacional não fazem parte deste ciclo.

## Próximo ciclo de implementação

A implementação pode ser fatiada em: fundação/Compose, servidor MCP e seus testes, schema e repositório Postgres, adaptadores do agente, API e testes de integração, e chat React. O primeiro ciclo técnico começa pela fundação e pelo MCP porque são pré-requisitos do restante.

