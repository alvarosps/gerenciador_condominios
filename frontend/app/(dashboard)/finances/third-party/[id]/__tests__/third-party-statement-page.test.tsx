import { describe, it, expect, vi, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useParams } from 'next/navigation';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import { createMockThirdPartyStatement } from '@/tests/mocks/data/finances';
import ThirdPartyStatementPage from '../page';

// Only next/navigation is mocked (a framework boundary, not an internal hook) — the same
// treatment the sidebar test gives it. Every data hook goes through MSW.
vi.mock('next/navigation', () => ({
  useParams: vi.fn(() => ({ id: '1' })),
}));

const API_BASE = 'http://localhost:8008/api';

function setStatementResponse(statement: ReturnType<typeof createMockThirdPartyStatement>) {
  server.use(
    http.get(`${API_BASE}/finances/third-party/statement/`, () => HttpResponse.json(statement))
  );
}

describe('ThirdPartyStatementPage (extrato mês a mês)', () => {
  beforeEach(() => {
    vi.mocked(useParams).mockReturnValue({ id: '1' });
    useAuthStore.setState({
      user: { id: 1, email: 'a@b.c', first_name: 'A', last_name: 'B', is_staff: true },
      isAuthenticated: true,
    });
  });

  it('exibe os StatCards de em aberto / atrasado / crédito lidos do backend', async () => {
    setStatementResponse(createMockThirdPartyStatement());

    const { queryClient } = renderWithProviders(<ThirdPartyStatementPage />);

    expect(await screen.findByText('Alvaro')).toBeInTheDocument();
    // "Em aberto" is both a StatCard label and a month badge, so it is matched by count.
    expect(screen.getAllByText('Em aberto').length).toBeGreaterThan(0);
    expect(screen.getByText('R$ 520,00')).toBeInTheDocument();
    expect(screen.getByText('R$ 400,00')).toBeInTheDocument();
    expect(screen.getAllByText('Crédito').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Atrasado').length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('renderiza os SEIS status com os rótulos PT corretos', async () => {
    setStatementResponse(createMockThirdPartyStatement());

    const { queryClient } = renderWithProviders(<ThirdPartyStatementPage />);

    await screen.findAllByText('Quitado');
    for (const label of ['Quitado', 'Sem movimento', 'Crédito', 'Atrasado', 'Parcial']) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
    // "Em aberto" is also the StatCard label, so the month badge is asserted via its own count.
    expect(screen.getAllByText('Em aberto').length).toBeGreaterThan(1);

    await waitForQueriesToSettle(queryClient);
  });

  it('NUNCA pinta o mês `empty` como sucesso — tom neutro, e nunca "Quitado" (bug da S79)', async () => {
    setStatementResponse(
      createMockThirdPartyStatement({
        months: [
          {
            month: '2026-03-01',
            devido: '0.00',
            aplicado: '0.00',
            resto: '0.00',
            status: 'empty',
            items: [],
          },
        ],
      })
    );

    const { queryClient } = renderWithProviders(<ThirdPartyStatementPage />);

    const [badge] = await screen.findAllByText('Sem movimento');
    expect(badge).toBeDefined();
    if (!badge) throw new Error('badge "Sem movimento" não encontrado');
    // The single month in the window is `empty`; "Quitado" must not appear anywhere.
    expect(screen.queryByText('Quitado')).not.toBeInTheDocument();
    expect(badge.className).toMatch(/muted|secondary/);
    expect(badge.className).not.toMatch(/success/);

    await waitForQueriesToSettle(queryClient);
  });

  it('o detalhe expansível mostra os itens (pagamentos e compras) que compõem o mês', async () => {
    setStatementResponse(createMockThirdPartyStatement());

    const { queryClient } = renderWithProviders(<ThirdPartyStatementPage />);

    await screen.findAllByText('Fevereiro de 2026');
    expect(screen.queryByText('Material de limpeza')).not.toBeInTheDocument();

    const [toggle] = screen.getAllByRole('button', { name: /detalhes de fevereiro de 2026/i });
    expect(toggle).toBeDefined();
    if (!toggle) throw new Error('toggle não encontrado');
    await userEvent.click(toggle);

    // Desktop table + mobile card each render the expanded detail.
    expect((await screen.findAllByText('Material de limpeza')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Compra').length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('mostra empty state PT quando a pessoa não tem movimento algum', async () => {
    setStatementResponse(
      createMockThirdPartyStatement({
        months: [],
        totals: {
          total_devido: '0.00',
          total_pago: '0.00',
          total_em_aberto: '0.00',
          total_atrasado: '0.00',
          saldo_credor: '0.00',
        },
      })
    );

    const { queryClient } = renderWithProviders(<ThirdPartyStatementPage />);

    expect(await screen.findByText('Nenhum movimento no período')).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('id inválido cai no estado de "não encontrado" sem chamar a API', async () => {
    vi.mocked(useParams).mockReturnValue({ id: 'abc' });
    let called = false;
    server.use(
      http.get(`${API_BASE}/finances/third-party/statement/`, () => {
        called = true;
        return HttpResponse.json(createMockThirdPartyStatement());
      })
    );

    renderWithProviders(<ThirdPartyStatementPage />);

    expect(await screen.findByText('Pessoa não encontrada')).toBeInTheDocument();
    expect(called).toBe(false);
  });

  it('erro 400 da API cai no estado de "não encontrado"', async () => {
    server.use(
      http.get(`${API_BASE}/finances/third-party/statement/`, () =>
        HttpResponse.json({ error: 'Pessoa não encontrada.' }, { status: 400 })
      )
    );

    renderWithProviders(<ThirdPartyStatementPage />);

    expect(await screen.findByText('Pessoa não encontrada')).toBeInTheDocument();
  });
});
