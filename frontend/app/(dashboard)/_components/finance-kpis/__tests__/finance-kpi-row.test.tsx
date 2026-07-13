import { describe, it, expect } from 'vitest';
import { http, HttpResponse, delay } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import {
  renderWithProviders,
  createTestQueryClient,
  waitForQueriesToSettle,
} from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockFinanceOverview } from '@/tests/mocks/data/finances';
import { FinanceKpiRow } from '../finance-kpi-row';

const API_BASE = 'http://localhost:8008/api';

function setOverviewResponse(overrides: Record<string, unknown> = {}) {
  server.use(
    http.get(`${API_BASE}/finances/finance-dashboard/overview/`, () =>
      HttpResponse.json(createMockFinanceOverview(overrides))
    )
  );
}

function setOverviewError() {
  server.use(
    http.get(`${API_BASE}/finances/finance-dashboard/overview/`, () =>
      HttpResponse.json({ detail: 'Erro interno' }, { status: 500 })
    )
  );
}

describe('FinanceKpiRow', () => {
  it('renders skeleton while loading', async () => {
    server.use(
      http.get(`${API_BASE}/finances/finance-dashboard/overview/`, async () => {
        await delay(50);
        return HttpResponse.json(createMockFinanceOverview());
      })
    );
    const queryClient = createTestQueryClient();
    const { container } = renderWithProviders(<FinanceKpiRow year={2026} month={6} />, {
      queryClient,
    });
    // Should have skeleton elements
    expect(
      container.querySelector('[data-slot="skeleton"]') ?? container.querySelector('.animate-pulse')
    ).toBeTruthy();
    await waitForQueriesToSettle(queryClient);
  });

  it('renders a PT error card when the overview query fails', async () => {
    setOverviewError();
    const queryClient = createTestQueryClient();
    renderWithProviders(<FinanceKpiRow year={2026} month={6} />, { queryClient });
    expect(await screen.findByText(/Erro ao carregar/i)).toBeInTheDocument();
  });

  it('renders all 5 KPI cards with server data (no local recompute)', async () => {
    setOverviewResponse();
    const queryClient = createTestQueryClient();
    renderWithProviders(<FinanceKpiRow year={2026} month={6} />, { queryClient });

    await waitFor(() => {
      // Use getAllByText since "Caixa" appears in label + "Caixa + Reserva" subLabel
      expect(screen.getAllByText(/Caixa/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Reserva/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/Resultado do Mês/i)).toBeInTheDocument();
      expect(screen.getByText(/Atrasados/i)).toBeInTheDocument();
      expect(screen.getByText(/Saldo Total/i)).toBeInTheDocument();
    });
    await waitForQueriesToSettle(queryClient);
  });

  it('displays overdue sub-label with rent info when rent_overdue > 0', async () => {
    setOverviewResponse({
      overdue_bills_total: '375.00',
      overdue_bills_count: 3,
      rent_overdue: { count: 1, total_fee: '75.00' },
      wedge_ok: false,
    });
    const queryClient = createTestQueryClient();
    renderWithProviders(<FinanceKpiRow year={2026} month={6} />, { queryClient });

    await waitFor(() => {
      // §4.4 — both figures are shown side by side (bills count AND rent overdue), not mutually exclusive.
      expect(screen.getByText(/3 contas em atraso.*Aluguel/i)).toBeInTheDocument();
    });
    await waitForQueriesToSettle(queryClient);
  });

  it('shows "Sem contas atrasadas" when overdue_bills_count is 0', async () => {
    setOverviewResponse({
      result_of_month: '0.00',
      cash_change_of_month: '0.00',
      cash_balance: '10000.00',
      total_balance: '15000.00',
      overdue_bills_total: '0.00',
      overdue_bills_count: 0,
      rent_overdue: { count: 0, total_fee: '0.00' },
    });
    const queryClient = createTestQueryClient();
    renderWithProviders(<FinanceKpiRow year={2026} month={6} />, { queryClient });

    await waitFor(() => {
      expect(screen.getByText('Sem contas atrasadas')).toBeInTheDocument();
    });
    await waitForQueriesToSettle(queryClient);
  });

  it('renders Caixa, Resultado and Saldo Total in destructive tone when negative (§4.3)', async () => {
    setOverviewResponse({
      result_of_month: '-300.00',
      cash_change_of_month: '-300.00',
      cash_balance: '-500.00',
      total_balance: '-800.00',
      overdue_bills_total: '0.00',
      overdue_bills_count: 0,
      rent_overdue: { count: 0, total_fee: '0.00' },
    });
    const queryClient = createTestQueryClient();
    renderWithProviders(<FinanceKpiRow year={2026} month={6} />, { queryClient });

    // Caixa can be negative (§4.3) → destructive; Resultado/Saldo Total flip by sign as well.
    expect(await screen.findByText(/R\$\s*500,00/)).toHaveClass('text-destructive');
    expect(screen.getByText(/R\$\s*300,00/)).toHaveClass('text-destructive');
    expect(screen.getByText(/R\$\s*800,00/)).toHaveClass('text-destructive');
    await waitForQueriesToSettle(queryClient);
  });

  it('passes buildingId to the request when provided', async () => {
    const captured: { buildingId: string | null } = { buildingId: null };
    server.use(
      http.get(`${API_BASE}/finances/finance-dashboard/overview/`, ({ request }) => {
        captured.buildingId = new URL(request.url).searchParams.get('building_id');
        return HttpResponse.json(createMockFinanceOverview());
      })
    );
    const queryClient = createTestQueryClient();
    renderWithProviders(<FinanceKpiRow year={2026} month={6} buildingId={42} />, { queryClient });
    await waitFor(() => expect(captured.buildingId).toBe('42'));
    await waitForQueriesToSettle(queryClient);
  });
});
