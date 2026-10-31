# Design System — Agente de Compras MCP

## Direção visual

Interface operacional escura, com linguagem editorial e técnica. O objetivo é fazer o pedido e a decisão de compra parecerem rastreáveis: uma grade sutil, metadados em monoespaçada e um único sinal quente para a ação principal. A densidade é baixa o suficiente para leitura rápida, mas os dados da requisição recebem tratamento preciso.

## Dials

- `DESIGN_VARIANCE: 4` — a tarefa de compra deve parecer familiar e confiável; a assinatura visual vem de tipografia, linhas e textura, não de assimetria.
- `MOTION_INTENSITY: 3` — feedback de estado e transições breves ajudam a explicar o processamento sem atrasar a tarefa.
- `VISUAL_DENSITY: 5` — há informações de preço e quantidade, mas uma única requisição deve caber em leitura confortável.

## Tokens

```css
:root {
  --bg-void: oklch(9% 0.012 250);
  --bg-base: oklch(13% 0.014 250);
  --bg-surface: oklch(18% 0.016 250);
  --bg-raised: oklch(23% 0.018 250);
  --text-primary: oklch(95% 0.006 250);
  --text-secondary: oklch(74% 0.01 250);
  --text-muted: oklch(54% 0.012 250);
  --accent: oklch(72% 0.14 55);
  --accent-hover: oklch(77% 0.13 55);
  --accent-active: oklch(64% 0.15 55);
  --accent-ink: oklch(14% 0.02 55);
  --focus: oklch(80% 0.16 55);
  --success: oklch(70% 0.13 150);
  --error: oklch(66% 0.19 25);
  --warning: oklch(78% 0.14 80);
  --border: oklch(95% 0.006 250 / 0.10);
  --border-strong: oklch(95% 0.006 250 / 0.18);
  --font-body: "Geist Sans", system-ui, sans-serif;
  --font-mono: "Geist Mono", ui-monospace, monospace;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
  --radius-control: 6px;
  --radius-panel: 12px;
  --ease: cubic-bezier(0.16, 1, 0.3, 1);
  --duration-micro: 150ms;
  --duration-ui: 220ms;
}
```

O fundo recebe uma textura de grão discreta em pseudo-elemento, com opacidade máxima de 0,035. Não usar gradientes decorativos, glassmorphism, sombras pretas nem cores saturadas fora dos estados semânticos.

## Estrutura da tela

1. **Barra superior:** marca textual `PURCHASE / MCP`, selo `LOCAL` ou `OPENROUTER` e divisor horizontal fino.
2. **Área de pedido:** título `Criar requisição`, texto de apoio breve, campo de texto com exemplo e botão `Analisar pedido`.
3. **Resultado:** aparece após a submissão; número de requisição em destaque monoespaçado, justificativa curta, tabela de itens e total alinhado à direita.
4. **Histórico curto:** até cinco requisições recentes, cada uma com número, data, estado e total.

No desktop, pedido e resultado ocupam duas colunas de proporção 5:7. No celular, tudo vira uma coluna, com o botão em largura total e a tabela de itens em cartões empilhados para evitar rolagem horizontal.

## Hierarquia tipográfica

- Título principal: Geist Sans, `clamp(2rem, 1.5rem + 2vw, 3rem)`, peso 600, tracking `-0.02em`.
- Rótulos e metadados: Geist Mono, 12–13px, maiúsculas, tracking `0.06em`.
- Corpo: Geist Sans, 16px, line-height 1.6.
- Valores monetários e número da requisição: Geist Mono, peso 600; o total tem tamanho mínimo de 24px.

## Componentes e estados

| Elemento | Normal | Hover | Focus | Active | Disabled | Loading | Error |
|---|---|---|---|---|---|---|---|
| Campo de pedido | superfície elevada e borda sutil | borda forte | anel de 2px em `--focus` | borda em `--accent` | opacidade 0,45 | cursor de espera | borda e texto auxiliar em `--error` |
| Botão primário | fundo `--accent`, texto escuro | `--accent-hover` | anel visível externo | `--accent-active`, deslocamento de 1px | cinza, sem cursor | spinner e rótulo `Analisando…` | indisponível até nova edição |
| Linha da requisição | superfície base | superfície elevada | contorno de foco | superfície elevada | não aplicável | esqueleto | selo de erro sem ocultar o pedido |
| Link secundário | texto secundário | texto primário, sublinhado | anel de foco | texto em accent | texto opaco | não aplicável | não aplicável |

Nenhum estado pode depender exclusivamente de cor. Ícones, texto e contraste complementam os sinais visuais.

## Estados da jornada

- **Inicial:** foco automático visual no campo, sem painel vazio competindo com a ação.
- **Processando:** manter o pedido legível; mostrar etapas neutras como `consultando catálogo` sem alegar ações que não ocorreram.
- **Sucesso:** painel com selo `REQUISIÇÃO CRIADA`, número, itens, quantidade, preço unitário e total.
- **Sem produto compatível:** bloco de aviso com o requisito não atendido e atalho para editar o pedido; nenhum número de requisição é exibido.
- **Catálogo ou agente indisponível:** mensagem humana, botão `Tentar novamente` e preservação do texto digitado.
- **Validação:** mensagem adjacente ao campo, nunca apenas um alerta global.

## Responsividade

| Faixa | Regra |
|---|---|
| Até 639px | 16px de margem lateral; uma coluna; histórico após o resultado; itens em cartões. |
| 640–1023px | 24px de margem lateral; resultado pode usar tabela compacta; controles preservam 44px de altura. |
| A partir de 1024px | container máximo de 1180px; grade de duas colunas; histórico em faixa inferior. |

## Movimento e acessibilidade

- Transições usam somente `opacity`, `transform`, `border-color` e `background-color`; duração padrão de 220ms com `--ease`.
- O resultado entra uma vez com fade e deslocamento vertical de 8px. Não há animação contínua fora do indicador de carregamento.
- Em `prefers-reduced-motion: reduce`, remover transições e substituir o spinner por texto estático.
- Todo controle tem alvo mínimo de 44×44px, foco de alto contraste e rótulo acessível.
- Texto normal deve manter contraste mínimo de 4,5:1; números e estados críticos devem ser lidos por leitores de tela através de região `aria-live` apropriada.

## Critério de fidelidade

A implementação deve transmitir uma ferramenta de trabalho precisa e noturna: camadas azul-acinzentadas, cobre usado apenas para decisão e ação, tipografia limpa e metadados técnicos. O conteúdo é exclusivamente do agente de compras; não reutilizar textos, marcas ou elementos de outros produtos.
