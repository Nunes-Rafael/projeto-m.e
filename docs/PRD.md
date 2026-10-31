# PRD — Agente de Compras MCP

## 1. Visão geral

Uma pessoa descreve uma necessidade de compra em linguagem natural. O Agente de Compras MCP consulta um catálogo de produtos, seleciona itens que atendam às restrições informadas e devolve uma requisição de compra registrada, com itens, quantidades, preços unitários e valor total.

O produto existe para transformar um pedido informal em uma requisição verificável, sem obrigar a pessoa a procurar manualmente no catálogo. Nesta etapa, o catálogo é o DummyJSON e a experiência é demonstrativa para o processo seletivo.

### Por que agora

O case avalia a capacidade de compreender um contexto de cliente, integrar sistemas e entregar uma solução reproduzível. O MVP precisa priorizar um fluxo completo e confiável, não sofisticação artificial de agente.

## 2. Público e problema

### Pessoa solicitante

Alguém que precisa comprar produtos para uma equipe e sabe expressar necessidade, quantidade e limites, mas não quer navegar por um catálogo item a item.

### Problema

Pedidos chegam em texto livre e exigem busca, comparação e registro manual. Sem uma resposta estruturada, há risco de escolher produto inadequado, ultrapassar um limite ou criar uma requisição com dados inventados.

## 3. Resultado esperado

Para um pedido como “preciso de 3 laptops para o time de vendas, até US$ 2.000 cada”, a pessoa recebe uma resposta com:

- número da requisição criada;
- produtos selecionados;
- quantidade por item;
- preço unitário e valor total;
- justificativa objetiva da escolha, quando aplicável.

Se o catálogo não oferecer uma alternativa compatível, a pessoa recebe uma explicação clara sobre a restrição não atendida. Nenhuma requisição inválida é criada.

## 4. Escopo do MVP

### Capacidades obrigatórias

1. Receber um pedido de compra em texto livre por uma tela de chat simples.
2. Permitir que o modelo decida quando consultar ferramentas de catálogo, sem uma sequência fixa de chamadas definida pela aplicação.
3. Disponibilizar duas capacidades de catálogo: buscar produtos por termo e consultar o detalhe de um produto pelo identificador.
4. Usar os dados retornados pelo catálogo para montar a resposta; o agente não pode inventar produtos, preços ou atributos.
5. Criar e persistir uma requisição quando houver itens que atendam ao pedido.
6. Listar as requisições de compra persistidas.
7. Apresentar uma mensagem compreensível ao usuário quando o catálogo estiver indisponível ou exceder o tempo esperado.
8. Permitir que o ambiente completo seja iniciado localmente com um único comando de composição de containers e que as tabelas necessárias sejam criadas automaticamente.
9. Documentar como executar o projeto e as principais decisões de produto e implementação.

### Restrições já confirmadas

- O teto informado no pedido é interpretado como teto por unidade. Portanto, no exemplo, cada laptop selecionado deve custar no máximo US$ 2.000.
- O projeto será desenvolvido como monorepo com áreas separadas para backend, servidor MCP e frontend.
- Backend e servidor MCP serão implementados em Python.
- O desenvolvimento local precisa funcionar sem chave de LLM; o adaptador para OpenRouter será preparado, porém desativado por padrão.

As decisões de arquitetura detalhada, persistência, contratos internos e escolha de bibliotecas permanecem para a etapa de arquitetura.

## 5. Histórias de usuário e critérios de aceite

### US-001 — Enviar um pedido

Como pessoa solicitante, quero escrever minha necessidade em um chat para iniciar uma requisição de compra sem preencher formulários técnicos.

Critérios de aceite:

- [ ] Consigo enviar um pedido em texto livre pela tela.
- [ ] A tela indica que a solicitação está sendo processada e não permite confundir o pedido em andamento com uma resposta final.
- [ ] Um pedido vazio não é enviado.

### US-002 — Encontrar alternativas no catálogo

Como pessoa solicitante, quero que o agente consulte o catálogo para que a recomendação seja baseada em dados reais.

Critérios de aceite:

- [ ] O modelo pode usar a busca e o detalhamento de produto conforme julgar necessário.
- [ ] A resposta só apresenta produtos e preços obtidos do catálogo.
- [ ] Para pedidos com teto por unidade, nenhum item recomendado ultrapassa o limite informado.

### US-003 — Receber uma requisição de compra válida

Como pessoa solicitante, quero receber uma requisição identificável com os itens e valores para poder conferir o resultado.

Critérios de aceite:

- [ ] Quando a compra é viável, a resposta mostra o número da requisição, itens, quantidades, preços unitários e valor total.
- [ ] A requisição fica disponível na listagem após sua criação.
- [ ] O valor total corresponde à soma de quantidade multiplicada pelo preço unitário de cada item.

### US-004 — Saber quando não há solução

Como pessoa solicitante, quero uma explicação quando o catálogo não atender ao pedido para poder ajustar minha necessidade.

Critérios de aceite:

- [ ] Se não houver produto compatível, a resposta informa qual requisito não foi atendido.
- [ ] Nessa situação, não é criada uma requisição de compra com dados fictícios ou itens incompatíveis.

### US-005 — Entender uma falha temporária

Como pessoa solicitante, quero receber uma mensagem clara quando o catálogo falhar ou demorar demais para saber que devo tentar novamente.

Critérios de aceite:

- [ ] Falha ou demora do catálogo não expõe mensagens internas, credenciais ou detalhes de infraestrutura.
- [ ] A tela explica que a consulta não pôde ser concluída e orienta uma nova tentativa.
- [ ] Não há persistência parcial de uma requisição após essa falha.

### US-006 — Reproduzir a demonstração

Como avaliador, quero iniciar todo o ambiente e seguir instruções curtas para validar a solução sem preparação manual adicional.

Critérios de aceite:

- [ ] O ambiente completo inicia com `docker compose up`.
- [ ] As estruturas de dados necessárias são criadas automaticamente.
- [ ] Há teste independente para cada ferramenta de catálogo, executável sem chave de LLM.
- [ ] O README explica execução local, variáveis de ambiente e principais escolhas.

## 6. Métricas e critérios de sucesso

O MVP será considerado pronto para o case quando:

- o pedido de exemplo gerar uma requisição persistida, com valores verificáveis e teto por unidade respeitado;
- uma busca sem alternativa compatível responder com transparência e sem salvar requisição;
- uma indisponibilidade do catálogo gerar mensagem clara no chat;
- os testes das duas ferramentas de catálogo passarem sem depender de chave de LLM;
- um avaliador conseguir subir os quatro componentes e repetir o fluxo seguindo apenas o README;
- nenhuma credencial estiver versionada, exibida na interface ou registrada em logs.

## 7. Fora de escopo

- Autenticação, perfis de usuário, permissões e fluxo de aprovação de compras.
- Integração com ERP, pagamento, e-mail, estoque ou fornecedores reais.
- Catálogo próprio, sincronização de estoque ou garantia de disponibilidade comercial.
- Histórico conversacional, memória de usuário, streaming de respostas ou interface avançada.
- Terceira ferramenta para persistir requisições via MCP; trata-se de melhoria opcional para depois do fluxo obrigatório.
- Execução do adaptador OpenRouter no desenvolvimento local padrão.

## 8. Riscos de produto e princípios de decisão

- O agente deve preferir declarar insuficiência de informação a recomendar um item sem evidência.
- Pedidos ambíguos devem resultar em uma pergunta objetiva ou em uma explicação clara da limitação, nunca em suposição silenciosa.
- A chave de API fornecida no material do case é segredo operacional: deve ser substituída/revogada se exposta e mantida fora do controle de versão.
- Diferenciais só devem ser incluídos depois que o fluxo obrigatório estiver funcional, testado e documentado.
