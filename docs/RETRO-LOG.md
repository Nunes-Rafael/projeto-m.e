# Retro Log

## Cycle: Avaliação do agente com LLM real — 2026-11-03

**Cycle Goal**: Medir decisões do modelo em cinco pedidos sintéticos com critérios verificáveis, mantendo catálogo/persistência isolados e a reserva estimada até US$ 0,50.

**Cumprido?**: Sim — a avaliação live concluiu 5/5 em 13 chamadas; a estimativa reportada foi US$ 0,00205 e os testes focados passaram 17/17.

**O que travou**:

- A regressão em `main_cli(None)` fez o parser consumir argumentos do processo pytest; Gohan corrigiu o caminho para usar argumentos explícitos.
- Uma warning de depreciação do Starlette/TestClient permanece. A suíte completa do backend não foi rodada nesta entrega.

**Muda no próximo Cycle**:

- Preservar a separação entre avaliação determinística em CI e avaliação live com opt-in duplo, fixtures e reserva estimada.
- Revalidar o perfil de preço e os limites antes de mudar o modelo; a reserva estimada não garante o valor faturado pelo provedor.
