import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders, createTestQueryClient } from '@/tests/test-utils';
import { FinanceKpiRow } from '../finance-kpi-row';
import type * as balanceHooks from '@/lib/api/hooks/use-finance-balance';

type FinanceOverviewResult = ReturnType<typeof balanceHooks.useFinanceOverview>;

// Use vi.hoisted so mock variables are available when vi.mock factories run
const { mockUseFinanceOverview } = vi.hoisted(() => ({
  mockUseFinanceOverview: vi.fn<typeof balanceHooks.useFinanceOverview>(),
}));

// Mock the hook so no real XHR is fired during this component test
vi.mock('@/lib/api/hooks/use-finance-balance', () => ({
  useFinanceOverview: mockUseFinanceOverview,
}));

describe('FinanceKpiRow', () => {
  beforeEach(() => {
    mockUseFinanceOverview.mockReset();
  });

  it('renders skeleton while loading', () => {
    mockUseFinanceOverview.mockReturnValue({ data: undefined, isLoading: true } as unknown as FinanceOverviewResult);
    const { container } = renderWithProviders(<FinanceKpiRow year={2026} month={6} />, {
      queryClient: createTestQueryClient(),
    });
    // Should have skeleton elements
    expect(container.querySelector('[data-slot="skeleton"]') ?? container.querySelector('.animate-pulse')).toBeTruthy();
  });

  it('renders nothing when not loading but no data', () => {
    mockUseFinanceOverview.mockReturnValue({ data: undefined, isLoading: false } as unknown as FinanceOverviewResult);
    const { container } = renderWithProviders(<FinanceKpiRow year={2026} month={6} />, {
      queryClient: createTestQueryClient(),
    });
    expect(container).toBeEmptyDOMElement();
  });

  it('renders all 5 KPI cards with server data (no local recompute)', async () => {
    mockUseFinanceOverview.mockReturnValue({
      isLoading: false,
      data: {
        year: 2026,
        month: 6,
        result_of_month: '2000.00',
        cash_change_of_month: '1500.00',
        cash_balance: '15000.00',
        reserve_balance: '5000.00',
        total_balance: '20000.00',
        overdue_bills_total: '300.00',
        overdue_bills_count: 2,
        rent_overdue: { count: 1, total_fee: '75.00' },
        wedge_ok: true,
      },
    } as unknown as FinanceOverviewResult);

    renderWithProviders(<FinanceKpiRow year={2026} month={6} />, {
      queryClient: createTestQueryClient(),
    });

    await waitFor(() => {
      // Use getAllByText since "Caixa" appears in label + "Caixa + Reserva" subLabel
      expect(screen.getAllByText(/Caixa/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Reserva/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/Resultado do Mês/i)).toBeInTheDocument();
      expect(screen.getByText(/Atrasados/i)).toBeInTheDocument();
      expect(screen.getByText(/Saldo Total/i)).toBeInTheDocument();
    });
  });

  it('displays overdue sub-label with rent info when rent_overdue > 0', async () => {
    mockUseFinanceOverview.mockReturnValue({
      isLoading: false,
      data: {
        year: 2026,
        month: 6,
        result_of_month: '2000.00',
        cash_change_of_month: '1500.00',
        cash_balance: '15000.00',
        reserve_balance: '5000.00',
        total_balance: '20000.00',
        overdue_bills_total: '375.00',
        overdue_bills_count: 3,
        rent_overdue: { count: 1, total_fee: '75.00' },
        wedge_ok: false,
      },
    } as unknown as FinanceOverviewResult);

    renderWithProviders(<FinanceKpiRow year={2026} month={6} />, {
      queryClient: createTestQueryClient(),
    });

    await waitFor(() => {
      expect(screen.getByText(/Aluguel atrasado/i)).toBeInTheDocument();
    });
  });

  it('shows "Sem atrasos" when overdue_bills_count is 0', async () => {
    mockUseFinanceOverview.mockReturnValue({
      isLoading: false,
      data: {
        year: 2026,
        month: 6,
        result_of_month: '0.00',
        cash_change_of_month: '0.00',
        cash_balance: '10000.00',
        reserve_balance: '5000.00',
        total_balance: '15000.00',
        overdue_bills_total: '0.00',
        overdue_bills_count: 0,
        rent_overdue: { count: 0, total_fee: '0.00' },
        wedge_ok: true,
      },
    } as unknown as FinanceOverviewResult);

    renderWithProviders(<FinanceKpiRow year={2026} month={6} />, {
      queryClient: createTestQueryClient(),
    });

    await waitFor(() => {
      expect(screen.getByText('Sem atrasos')).toBeInTheDocument();
    });
  });

  it('renders Caixa, Resultado and Saldo Total in destructive tone when negative (§4.3)', async () => {
    mockUseFinanceOverview.mockReturnValue({
      isLoading: false,
      data: {
        year: 2026,
        month: 6,
        result_of_month: '-300.00',
        cash_change_of_month: '-300.00',
        cash_balance: '-500.00',
        reserve_balance: '5000.00',
        total_balance: '-800.00',
        overdue_bills_total: '0.00',
        overdue_bills_count: 0,
        rent_overdue: { count: 0, total_fee: '0.00' },
        wedge_ok: true,
      },
    } as unknown as FinanceOverviewResult);

    renderWithProviders(<FinanceKpiRow year={2026} month={6} />, {
      queryClient: createTestQueryClient(),
    });

    // Caixa can be negative (§4.3) → destructive; Resultado/Saldo Total flip by sign as well.
    expect(await screen.findByText(/R\$\s*500,00/)).toHaveClass('text-destructive');
    expect(screen.getByText(/R\$\s*300,00/)).toHaveClass('text-destructive');
    expect(screen.getByText(/R\$\s*800,00/)).toHaveClass('text-destructive');
  });

  it('passes buildingId to hook when provided', () => {
    mockUseFinanceOverview.mockReturnValue({ data: undefined, isLoading: false } as unknown as FinanceOverviewResult);
    renderWithProviders(<FinanceKpiRow year={2026} month={6} buildingId={42} />, {
      queryClient: createTestQueryClient(),
    });
    expect(mockUseFinanceOverview).toHaveBeenCalledWith(2026, 6, 42);
  });
});
