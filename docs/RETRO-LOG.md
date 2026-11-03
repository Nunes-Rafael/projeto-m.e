# Retro Log

## Cycle: Avaliação do agente com LLM real — 2026-11-03

**Cycle Goal**: Medir decisões do modelo em cinco pedidos sintéticos com critérios verificáveis, mantendo catálogo/persistência isolados e a reserva estimada até US$ 0,50.

**Cumprido?**: Sim — a avaliação live concluiu 5/5 em 13 chamadas; a estimativa reportada foi US$ 0,00205. Os testes focados passaram 17/17, a suíte completa do backend 42/42 e a suíte MCP 20/20. A integração de serviços foi validada em Compose descartável; depois, Rafael validou manualmente o fluxo feliz com OpenAI no navegador e conferiu a persistência no PostgreSQL.

**O que travou**:

- A regressão em `main_cli(None)` fez o parser consumir argumentos do processo pytest; Gohan corrigiu o caminho para usar argumentos explícitos.
- Permanecem avisos de depreciação no Starlette/TestClient e em dependências do servidor MCP; não impediram a conclusão das suítes.
- A CI passou nos três jobs no commit `9731db0`. Commits posteriores precisam de nova execução para confirmar a versão atual. A validação de serviços criou e listou uma requisição usando DummyJSON, tools MCP e PostgreSQL descartável, sem chave de LLM. O fluxo manual posterior usou OpenAI e confirmou a gravação; a automação de browser e os fluxos de erro/retry da Story do Ciclo 03 permanecem pendentes.

**Muda no próximo Cycle**:

- Preservar a separação entre avaliação determinística em CI e avaliação live com opt-in duplo, fixtures e reserva estimada.
- Revalidar o perfil de preço e os limites antes de mudar o modelo; a reserva estimada não garante o valor faturado pelo provedor.
