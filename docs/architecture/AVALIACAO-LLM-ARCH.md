# ARCH — Avaliação do agente com LLM real

## 1. Objetivo e limite

Complementar a avaliação determinística existente com cinco pedidos sintéticos processados pelo agente OpenAI configurado no projeto. O modo real mede seleção de produto e respeito às restrições com um modelo real; os cenários, catálogo, validação de compra e persistência continuam controlados por fixtures locais.

Este comando não deve usar PostgreSQL, servidor MCP, DummyJSON ou qualquer outro serviço de persistência/catálogo real. Ele não simula disponibilidade do catálogo de produção nem substitui os testes determinísticos de falha. Nenhum dado digitado por uma pessoa deve ser enviado: somente os cinco pedidos sintéticos versionados para a avaliação.

## 2. Modos e execução explícita

- `python -m evaluation.run`: mantém a avaliação determinística atual como modo padrão, sem provedor e sem rede.
- `python -m evaluation.run --live --confirm-paid --max-cost-usd 0.50`: modo real, manual e explícito. Exige `AGENT_MODE=openai`, `OPENAI_API_KEY` e `OPENAI_MODEL=gpt-5.4-nano`.

O modo real deve recusar início se faltar qualquer flag de opt-in, se houver configuração incompatível ou se a estimativa de limite exceder o máximo aprovado de US$ 0,50. `--max-cost-usd` pode reduzir o limite, nunca elevá-lo. A saída prévia deve informar modelo, quantidade máxima de cenários/chamadas, limites de tokens e estimativa conservadora antes da primeira chamada. Não imprimir prompts, argumentos, cabeçalhos, corpo HTTP, resposta completa ou chave.

A execução deve obter o agente por `get_purchase_agent()` e chamar `decide` diretamente, sem percorrer o endpoint HTTP de criação de requisição. Cada cenário usa uma instância nova do catálogo de fixture e de um gravador em memória compatível com `ExecutionCatalog`; o método de gravação registra o resultado apenas na memória. Assim se testa o fluxo do agente e as validações do backend sem importar efeitos reais de persistência.

## 3. Modelo de dados e oráculo dos cinco cenários

Os cinco pedidos são sintéticos e cada um declara no código da fixture:

- texto do pedido;
- catálogo pequeno e determinístico com títulos, IDs e preços;
- conjunto de produtos aceitos (pode haver mais de uma resposta válida);
- quantidade esperada e eventual teto unitário;
- critério de pontuação.

O oráculo pontua cada cenário pelas propriedades observáveis:

1. agente concluiu sem erro de provedor ou contrato;
2. a ferramenta de busca foi chamada e todos os produtos escolhidos pertencem ao conjunto esperado e aos resultados da fixture;
3. quantidades correspondem ao pedido;
4. nenhum preço unitário ultrapassa o teto;
5. total confere com preço unitário × quantidade;
6. exatamente uma requisição foi criada no gravador em memória, com os mesmos itens validados.

Não comparar justificativa em prosa por igualdade literal. Cada cenário recebe `PASS` ou `FAIL`, com uma explicação curta que não contenha prompts ou resposta textual completa. A pontuação total é `N/5`; código de saída `0` somente para cinco aprovações. Cenários sobre timeout, produto ausente e falha de persistência continuam na avaliação determinística: são testes de integração/controlos, não uma medida útil da capacidade de seleção do LLM.

## 4. Isolamento de rede e persistência

- A única chamada de rede permitida é para `https://api.openai.com/v1/chat/completions`, através do adaptador já usado por `AGENT_MODE=openai`.
- Catálogo sintético serve `buscar_produtos` e `detalhar_produto` localmente. O adaptador de persistência é em memória.
- Não criar `CatalogMcpClient`, abrir conexão PostgreSQL ou chamar `POST /requisicoes` no modo real. A implementação deve tornar isso verificável injetando as fixtures diretamente na execução do agente.
- Um cenário não pode reutilizar IDs, estado ou resultados de outro. O comando termina depois dos cinco casos ou assim que atingir falha de configuração/custo.
- Sem retry automático de HTTP, retry de cenário, fallback para outro provedor/modelo ou repetição silenciosa de chamada. Uma falha encerra o cenário; não dispara tentativa paga adicional.

## 5. Perfil de preço aprovado e controle de custo

Perfil autorizado para esta implementação:

| Parâmetro | Valor aprovado |
|---|---:|
| `OPENAI_MODEL` | `gpt-5.4-nano` |
| Entrada | US$ 0,20 por milhão de tokens ([preço oficial](https://developers.openai.com/api/docs/models/gpt-5.4-nano), consultado em 2026-11-03) |
| Saída | US$ 1,25 por milhão de tokens ([preço oficial](https://developers.openai.com/api/docs/models/gpt-5.4-nano), consultado em 2026-11-03) |
| Teto selecionável por execução | US$ 0,50 |
| Teto máximo da reserva estimada pelo programa | US$ 0,50 |
| Cenários máximos | 5 |
| Chamadas de provedor máximas | 6 por cenário (30 no total) |
| Tokens de saída máximos | 512 por chamada, via `max_completion_tokens` |
| Corpo HTTP máximo enviado | 32 KiB por chamada |

O controle deve falhar fechado se `OPENAI_MODEL` não corresponder exatamente ao perfil aprovado, se a taxa associada ao perfil não for exatamente a dupla de valores aprovada ou se o limite solicitado exceder US$ 0,50. Tarifas são dados versionados no código/configuração; não há consulta automática a uma API oficial de preços. Portanto, o programa só valida a correspondência com o perfil aprovado embutido. Uma mudança pública de tarifa pode ocorrer sem o programa detectá-la: antes de atualizar esse perfil ou rodar a avaliação após uma mudança conhecida de preços, deve-se revalidar a fonte oficial e revisar esta arquitetura.

### Reserva e estimativa por chamada

Antes de cada chamada, serializar o corpo que será enviado, rejeitá-lo se ultrapassar 32 KiB e reservar no orçamento o custo de limite daquela chamada. Para a estimativa conservadora de entrada usar `bytes_do_corpo + 4.096` tokens; para saída usar o máximo de 512 tokens. O acréscimo de 4.096 é margem operacional estimada, não um limite garantido pelo tokenizer nem uma medida emitida pela OpenAI.

Com 32.768 bytes, 4.096 tokens de margem, 512 tokens de saída e 30 chamadas máximas:

```text
tokens de entrada estimados por chamada = 32.768 + 4.096 = 36.864
custo estimado máximo sem margem = 30 × ((36.864 × 0,20) + (512 × 1,25)) / 1.000.000
                                   = US$ 0,240384
reserva com margem operacional de 25% = US$ 0,30048
```

Os custos são estimativas calculadas com o perfil local de preço; não representam a fatura final. O runtime deve manter, para todas as chamadas da execução, uma reserva acumulada que nunca exceda o `--max-cost-usd` aprovado. Antes de enviar uma chamada, reservar seu limite estimado (incluindo margem); se a reserva ultrapassar o teto, não enviar essa chamada. Após uma resposta com `usage` válido, contabilizar `prompt_tokens` e `completion_tokens` com as taxas aprovadas. Para a estimativa de segurança, não descontar cached input tokens. Quando `usage` estiver ausente ou malformado, preservar a reserva máxima da chamada corrente, encerrar a execução imediatamente e não fazer novas chamadas.

Mostrar no relatório o total de chamadas, tokens de entrada/saída reportados, reserva/estimativa e o perfil/modelo. O campo `usage` da resposta do provedor é a observação de tokens da API; o painel de uso/faturamento da OpenAI é a fonte de cobrança efetiva. Preços ou tokens extras contabilizados pelo provedor, mudanças posteriores de tarifa, regras de faturamento e eventuais diferenças de tokenização não são controláveis pelo cliente HTTP. Portanto, o guard reduz e limita a exposição estimada, mas não promete um teto absoluto sobre a cobrança da conta.

## 6. Segredos e saída

- Ler `OPENAI_API_KEY` apenas do ambiente local. Nunca aceitar chave em argumento, gravar em fixture, arquivo versionado, teste, output ou log.
- Enviar apenas os pedidos sintéticos aprovados e as respostas de produto de fixture para o provedor.
- Não registrar prompts, cabeçalhos, corpo HTTP, respostas completas, justificativa, segredo ou erro bruto do provedor. Erros devem ser convertidos em códigos curtos por cenário.
- Resultado por caso: `PASS`/`FAIL` e motivo controlado; resumo `N/5`, modelo, número de chamadas e uso/estimativa de tokens/custo.
- A estimativa não deve incluir conteúdo da requisição; não imprimir até mesmo o pedido sintético na saída resumida.

## 7. CI, testes e critérios de aceite

O modo determinístico existente continua no workflow da CI. O modo `--live` não pode ser chamado por teste automatizado, CI, build, Compose, startup da aplicação ou comando padrão. CI mantém segredos de provedor vazios.

Critérios verificáveis para a implementação:

- [ ] Comando padrão ainda executa somente os cenários determinísticos, sem rede ou segredo.
- [ ] `--live` sem `--confirm-paid`, com modo diferente de OpenAI, sem chave, modelo diferente ou perfil de preço divergente falha antes de qualquer chamada HTTP.
- [ ] Teto informado maior que US$ 0,50 é rejeitado; teto menor é aceito e aplicado como teto global da estimativa.
- [ ] Teste unitário prova que reserva projetada acima do teto recusa a chamada antes do envio.
- [ ] Corpo acima de 32 KiB e saída configurada acima de 512 tokens são recusados antes do envio.
- [ ] Sem `usage` válido, a execução interrompe sem retry e sem nova chamada.
- [ ] Fixtures, gravador em memória e verificação de dependências provam que nenhum acesso a PostgreSQL, MCP ou DummyJSON ocorre.
- [ ] Os cinco cenários mostram score por critérios objetivos, `N/5`, chamadas e uso estimado/reportado; saída não contém prompt, resposta integral, segredo ou header.
- [ ] O workflow da CI continua sem executar `--live` e sem carregar uma chave real.
- [ ] Uma execução live manual autorizada permanece opt-in e permite no máximo cinco casos e seis chamadas HTTP por caso.

## 8. Trade-offs e limitações

- A avaliação exerce o LLM e a decisão de uso das tools, mas mantém dados e gravação sintéticos; não testa se a API DummyJSON ou o banco real estão funcionando.
- O orçamento é uma barreira de estimativa baseada em payload limitado, teto de saída e preço conhecido. Tokenização interna, tarifas alteradas, contabilidade do provedor e falhas após aceite do request podem tornar a cobrança real diferente.
- Não há retry: isso sacrifica resiliência em favor de limite de custo previsível.
- Um 5/5 é evidência para estes cinco prompts e estas fixtures, não uma estimativa estatística de acurácia geral nem garantia de comportamento em produção.
- `gpt-5.4-nano` e suas tarifas formam o perfil aprovado atual. Qualquer troca de modelo/tarifa exige revisão do perfil, teto estimado e critérios antes de permitir novas chamadas live.
