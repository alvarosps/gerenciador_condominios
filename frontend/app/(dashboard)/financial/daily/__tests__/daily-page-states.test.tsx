import { describe, it, expect, vi, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import {
  renderWithProviders,
  waitForQueriesToSettle,
  createTestQueryClient,
} from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import DailyControlPage from '../page';

const API_BASE = 'http://localhost:8008/api';

// Mock chart component — Recharts requires ResizeObserver which is not available in happy-dom
vi.mock('../_components/daily-balance-chart', () => ({
  DailyBalanceChart: () => <div data-testid="daily-balance-chart" />,
}));

vi.mock('../_components/day-detail-drawer', () => ({
  DayDetailDrawer: () => null,
}));

vi.mock('@/app/(dashboard)/financial/expenses/_components/expense-form-modal', () => ({
  ExpenseFormModal: () => null,
}));

describe('DailyControlPage error and empty states', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: {
        id: 1,
        email: 'admin@example.com',
        first_name: 'Admin',
        last_name: 'User',
        is_staff: true,
      },
      isAuthenticated: true,
    });
  });

  it('shows an error alert with a retry action when the breakdown request fails', async () => {
    server.use(
      http.get(`${API_BASE}/daily-control/breakdown/`, () =>
        HttpResponse.json({ detail: 'Erro interno' }, { status: 500 })
      )
    );
    const queryClient = createTestQueryClient();

    renderWithProviders(<DailyControlPage />, { queryClient });

    expect(await screen.findByText(/erro ao carregar o controle diário/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /tentar novamente/i })).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('shows a friendly empty state when the month has no movements', async () => {
    server.use(http.get(`${API_BASE}/daily-control/breakdown/`, () => HttpResponse.json([])));
    const queryClient = createTestQueryClient();

    renderWithProviders(<DailyControlPage />, { queryClient });

    await waitFor(() => {
      expect(screen.getByText(/nenhum lançamento em/i)).toBeInTheDocument();
    });

    await waitForQueriesToSettle(queryClient);
  });
});
