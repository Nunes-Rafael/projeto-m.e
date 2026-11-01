# Story 1: Interface operacional React

## Status

Approved

## Módulo

Interface e entrega final

## Alocado a

Vegeta

## Dependências

Ciclo 02 concluído.

## Prioridade

Crítica.

## Contexto completo

O frontend segue o documento de design aprovado: fundo escuro azul-acinzentado, tipografia Geist, grade/hairlines sutis e cobre apenas como sinal de ação. A tela contém barra superior com modo, pedido, resultado e histórico curto. Desktop usa duas colunas 5:7; mobile usa coluna única. Todos os controles têm 44px mínimos, foco visível e respeito a redução de movimento.

## O que fazer

Criar a estrutura React/Vite, tokens e componentes de apresentação para formulário, resultado, histórico e estados visuais. Nesta story, usar dados controlados ou interfaces locais; a integração HTTP fica na story seguinte.

## Critérios de aceite

- [ ] Interface reproduz fielmente hierarquia, tokens e responsividade do documento de design.
- [ ] Formulário, painel de resposta e histórico possuem estados inicial, carregando, sucesso, erro e indisponibilidade.
- [ ] Resultado mostra número, itens, quantidade, preço unitário, total e justificativa.
- [ ] Nenhum estado depende apenas de cor; foco e `prefers-reduced-motion` estão cobertos.
- [ ] Não há marca, conteúdo ou identidade de outro projeto reutilizados.

## Log de execução

| Data | Status | Nota |
|---|---|---|
| 2026-10-31 | Draft | Story criada a partir do contrato visual aprovado para evitar improviso de UI. |
