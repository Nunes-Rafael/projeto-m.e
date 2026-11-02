import { useCallback, useEffect, useState } from 'react';

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const MCP_TOOL_NAMES = new Set(['buscar_produtos', 'detalhar_produto', 'criar_requisicao']);
const money = (value) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
const date = (value) => new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));

async function request(path, options) {
  let response;
  try { response = await fetch(`${API}${path}`, options); }
  catch { throw new Error('Não foi possível conectar ao serviço. Verifique se o ambiente está ativo e tente novamente.'); }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.erro?.mensagem || 'O pedido não pôde ser processado. Tente novamente.');
  return body;
}

function App() {
  const [pedido, setPedido] = useState('');
  const [requisicao, setRequisicao] = useState(null);
  const [historico, setHistorico] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [mode, setMode] = useState('local');

  const loadHistory = useCallback(async () => {
    try {
      const data = await request('/requisicoes');
      setHistorico(data.requisicoes.slice(0, 5));
    } catch { setHistorico([]); }
  }, []);

  useEffect(() => {
    loadHistory();
    fetch(`${API}/health`).then((res) => { if (!res.ok) throw new Error(); setMode('local'); }).catch(() => setMode('offline'));
  }, [loadHistory]);

  async function submit(event) {
    event.preventDefault();
    if (!pedido.trim() || busy) return;
    setBusy(true); setError(''); setRequisicao(null);
    try {
      const data = await request('/requisicoes', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ pedido }) });
      setRequisicao(data.requisicao);
      await loadHistory();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  return <div className="shell">
    <header className="topbar"><a className="wordmark" href="#top">PURCHASE <span>/</span> MCP</a><div className="top-meta"><span className="status-dot" />{mode === 'offline' ? 'SERVIÇO INDISPONÍVEL' : mode.toUpperCase()}<span className="serial">LOCAL PROCUREMENT TOOL · 01</span></div></header>
    <main id="top">
      <section className="intro"><p className="eyebrow">CATALOGUE ASSISTANT <span>—</span> PROCUREMENT</p><h1>Uma boa compra<br /><em>começa com clareza.</em></h1><p className="lede">Descreva o que sua equipe precisa. O agente consulta o catálogo e prepara uma requisição com valores conferidos.</p></section>
      <div className="workspace">
        <section className="panel request-panel" aria-labelledby="request-title">
          <div className="panel-heading"><span className="eyebrow">01 / NOVA SOLICITAÇÃO</span><span className="panel-mark">↘</span></div>
          <h2 id="request-title">Criar requisição</h2><p className="helper">Inclua produto, quantidade e qualquer limite importante.</p>
          <form onSubmit={submit}>
            <label htmlFor="pedido">O QUE VOCÊ PRECISA?</label>
            <textarea id="pedido" value={pedido} onChange={(event) => { setPedido(event.target.value); if (error) setError(''); }} placeholder="Ex.: Preciso de 3 laptops para o time de vendas, até US$ 2.000 cada." maxLength={2000} aria-describedby={error ? 'form-error' : 'char-count'} aria-invalid={Boolean(error)} />
            <div className="field-foot"><span id={error ? 'form-error' : 'char-count'} className={error ? 'error-copy' : ''}>{error || `${pedido.length} / 2.000`}</span><span>SEJA ESPECÍFICO</span></div>
            <button className="primary" type="submit" disabled={busy || !pedido.trim()}>{busy ? <><span className="spinner" aria-hidden="true" /> Analisando pedido…</> : <>Analisar pedido <span aria-hidden="true">↗</span></>}</button>
          </form>
          <div className="privacy-note"><span>i</span> A requisição só é criada quando há um produto compatível.</div>
        </section>
        <section className="panel result-panel" aria-labelledby="result-title" aria-live="polite">
          <div className="panel-heading"><span className="eyebrow">02 / RESULTADO</span><span className="panel-mark">{requisicao ? '✓' : '—'}</span></div>
          {busy ? <div className="empty-state loading-state"><span className="loader-ring" /><h2 id="result-title">Consultando catálogo</h2><p>Conferindo opções e preparando os valores.</p><div className="progress-line"><i /></div></div> : requisicao ? <div className="result-content">
            <span className="success-label"><span>✓</span> REQUISIÇÃO CRIADA</span><h2 id="result-title">Pedido <b>#{String(requisicao.numero).padStart(4, '0')}</b></h2><p className="reason">{requisicao.justificativa}</p>
            {Array.isArray(requisicao.ferramentasChamadas) && requisicao.ferramentasChamadas.some((name) => MCP_TOOL_NAMES.has(name)) && <div className="tools-used"><span>FERRAMENTAS MCP</span><ul aria-label="Ferramentas MCP executadas">{[...new Set(requisicao.ferramentasChamadas.filter((name) => MCP_TOOL_NAMES.has(name)))].map((name) => <li key={name}>{name}</li>)}</ul></div>}
            <div className="items-table"><div className="table-head"><span>ITEM</span><span>QTD.</span><span>UNITÁRIO</span><span>TOTAL</span></div>{requisicao.itens.map((item) => <div className="item-row" key={item.produtoId}><span className="product-name">{item.titulo}<small>CATÁLOGO · #{item.produtoId}</small></span><span data-label="Qtd.">{item.quantidade}</span><span data-label="Unitário">{money(item.precoUnitario)}</span><span data-label="Total">{money(item.valorTotal)}</span></div>)}</div>
            <div className="total-row"><span>VALOR TOTAL</span><strong>{money(requisicao.valorTotal)}</strong></div>
          </div> : error ? <div className="empty-state error-state"><span className="state-icon">!</span><h2 id="result-title">Não foi possível concluir</h2><p>{error}</p><div className="error-actions"><button type="button" className="text-button" onClick={(event) => submit(event)} disabled={busy || !pedido.trim()}>Tentar novamente <span>↻</span></button><button type="button" className="text-button" onClick={() => setError('')}>Editar pedido <span>↗</span></button></div></div> : <div className="empty-state"><span className="state-index">AWAITING INPUT <b>00</b></span><div className="empty-glyph" aria-hidden="true">＋</div><h2 id="result-title">Sua requisição<br />aparece aqui.</h2><p>Os itens selecionados, os preços e o total ficam reunidos neste painel.</p></div>}
          {requisicao && <div className="result-stamp"><span>REGISTRADO</span><time>{date(requisicao.criadaEm)}</time></div>}
        </section>
      </div>
      <section className="history" aria-labelledby="history-title"><div className="history-heading"><div><p className="eyebrow">03 / REGISTRO</p><h2 id="history-title">Requisições recentes</h2></div><span className="history-count">{String(historico.length).padStart(2, '0')} <small>ÚLTIMAS</small></span></div>
        {historico.length ? <div className="history-list">{historico.map((item) => <article className="history-item" key={item.numero}><span className="history-number">#{String(item.numero).padStart(4, '0')}</span><span className="history-request">{item.pedido}</span><span className="history-status"><i /> {item.status}</span><strong>{money(item.valorTotal)}</strong><time>{date(item.criadaEm)}</time></article>)}</div> : <p className="history-empty">As requisições criadas aparecerão aqui.</p>}
      </section>
    </main>
    <footer><span>PURCHASE / MCP</span><span>DECISÕES CLARAS. REQUISIÇÕES CONFERIDAS.</span><span>DEMO BUILD · 2026</span></footer>
  </div>;
}

export default App;
