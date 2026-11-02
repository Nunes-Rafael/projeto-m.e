import '@testing-library/jest-dom/vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App.jsx';

function response(body, ok = true) {
  return Promise.resolve({ ok, json: () => Promise.resolve(body) });
}

function requisition({ ferramentasChamadas, includeTools = true } = {}) {
  return {
    requisicao: {
      numero: 12,
      pedido: 'dois notebooks',
      itens: [{ produtoId: 78, titulo: 'Notebook', quantidade: 2, precoUnitario: 100, valorTotal: 200 }],
      valorTotal: 200,
      justificativa: 'Opção compatível encontrada.',
      criadaEm: '2026-11-02T12:00:00Z',
      ...(includeTools ? { ferramentasChamadas } : {}),
    },
  };
}

function mockInitialRequests() {
  global.fetch.mockImplementation((url) => {
    if (url.endsWith('/health')) return response({ status: 'ok' });
    if (url.endsWith('/requisicoes')) return response({ requisicoes: [] });
    throw new Error(`Fetch inesperado: ${url}`);
  });
}

async function submitRequest() {
  fireEvent.change(screen.getByLabelText('O QUE VOCÊ PRECISA?'), { target: { value: 'dois notebooks' } });
  fireEvent.click(screen.getByRole('button', { name: /analisar pedido/i }));
}

describe('telemetria de ferramentas MCP no resultado', () => {
  beforeEach(() => {
    global.fetch = vi.fn();
    mockInitialRequests();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('mostra as ferramentas permitidas chamadas e omite nomes desconhecidos', async () => {
    global.fetch.mockImplementation((url, options) => {
      if (options?.method === 'POST') return response(requisition({ ferramentasChamadas: ['buscar_produtos', 'detalhar_produto', 'criar_requisicao', 'interna_nao_permitida'] }));
      if (url.endsWith('/health')) return response({ status: 'ok' });
      if (url.endsWith('/requisicoes')) return response({ requisicoes: [] });
      throw new Error(`Fetch inesperado: ${url}`);
    });

    render(<App />);
    await submitRequest();

    expect(await screen.findByLabelText('Ferramentas MCP executadas')).toBeInTheDocument();
    expect(screen.getByText('buscar_produtos')).toBeInTheDocument();
    expect(screen.getByText('detalhar_produto')).toBeInTheDocument();
    expect(screen.getByText('criar_requisicao')).toBeInTheDocument();
    expect(screen.queryByText('interna_nao_permitida')).not.toBeInTheDocument();
  });

  it.each([{ ferramentasChamadas: [] }, { includeTools: false }])('não renderiza o bloco quando a lista está vazia ou ausente', async (toolField) => {
    global.fetch.mockImplementation((url, options) => {
      if (options?.method === 'POST') return response(requisition(toolField));
      if (url.endsWith('/health')) return response({ status: 'ok' });
      if (url.endsWith('/requisicoes')) return response({ requisicoes: [] });
      throw new Error(`Fetch inesperado: ${url}`);
    });

    render(<App />);
    await submitRequest();

    await screen.findByRole('heading', { name: /Pedido/ });
    expect(screen.queryByLabelText('Ferramentas MCP executadas')).not.toBeInTheDocument();
  });

  it('limpa as ferramentas anteriores ao iniciar outro envio e mantém limpo após falha', async () => {
    let postCount = 0;
    global.fetch.mockImplementation((url, options) => {
      if (options?.method === 'POST') {
        postCount += 1;
        if (postCount === 1) return response(requisition({ ferramentasChamadas: ['buscar_produtos'] }));
        return response({ erro: { mensagem: 'Falha controlada.' } }, false);
      }
      if (url.endsWith('/health')) return response({ status: 'ok' });
      if (url.endsWith('/requisicoes')) return response({ requisicoes: [] });
      throw new Error(`Fetch inesperado: ${url}`);
    });

    render(<App />);
    await submitRequest();
    expect(await screen.findByText('buscar_produtos')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /analisar pedido/i }));
    await waitFor(() => expect(screen.getByText('Consultando catálogo')).toBeInTheDocument());
    expect(screen.queryByText('buscar_produtos')).not.toBeInTheDocument();
    expect((await screen.findAllByText('Falha controlada.')).length).toBeGreaterThan(0);
    expect(screen.queryByText('buscar_produtos')).not.toBeInTheDocument();
  });
});
