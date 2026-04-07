import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { useAuthStore } from '@/store/auth-store';
import DailyControlPage from '../page';

// Mock chart component — Recharts requires ResizeObserver which is not available in happy-dom
vi.mock('../_components/daily-balance-chart', () => ({
  DailyBalanceChart: () => <div data-testid="daily-balance-chart" />,
}));

// Mock timeline — complex component not under test here
vi.mock('../_components/daily-timeline', () => ({
  DailyTimeline: () => <div data-testid="daily-timeline" />,
}));

// Mock day detail drawer
vi.mock('../_components/day-detail-drawer', () => ({
  DayDetailDrawer: () => null,
}));

// Mock expense form modal
vi.mock('@/app/(dashboard)/financial/expenses/_components/expense-form-modal', () => ({
  ExpenseFormModal: () => null,
}));

describe('DailyControlPage admin gating', () => {
  beforeEach(() => {
    useAuthStore.setState({
      token: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
    });
  });

  it('hides add expense buttons for non-admin users', async () => {
    useAuthStore.setState({
      user: {
        id: 1,
        email: 'user@example.com',
        first_name: 'User',
        last_name: 'Test',
        is_staff: false,
      },
      isAuthenticated: true,
      token: 'fake-token',
      refreshToken: 'fake-refresh',
    });

    renderWithProviders(<DailyControlPage />);

    await waitFor(() => {
      expect(screen.getByText('Controle Diário')).toBeInTheDocument();
    });

    // Non-admin users should not see "Nova Despesa" buttons
    expect(screen.queryByText(/nova despesa/i)).not.toBeInTheDocument();
  });

  it('shows add expense buttons for admin users', async () => {
    useAuthStore.setState({
      user: {
        id: 2,
        email: 'admin@example.com',
        first_name: 'Admin',
        last_name: 'User',
        is_staff: true,
      },
      isAuthenticated: true,
      token: 'fake-admin-token',
      refreshToken: 'fake-admin-refresh',
    });

    renderWithProviders(<DailyControlPage />);

    await waitFor(() => {
      expect(screen.getByText('Controle Diário')).toBeInTheDocument();
    });

    // Admin users should see both "Nova Despesa" buttons (current month + next month)
    const addButtons = screen.getAllByText(/nova despesa/i);
    expect(addButtons.length).toBeGreaterThanOrEqual(1);
  });

  it('renders navigation controls for all users', async () => {
    useAuthStore.setState({
      user: {
        id: 1,
        email: 'user@example.com',
        first_name: 'User',
        last_name: 'Test',
        is_staff: false,
      },
      isAuthenticated: true,
      token: 'fake-token',
      refreshToken: 'fake-refresh',
    });

    renderWithProviders(<DailyControlPage />);

    await waitFor(() => {
      expect(screen.getByText('Controle Diário')).toBeInTheDocument();
    });

    // Month navigation buttons are always visible
    expect(screen.getByRole('button', { name: /mês anterior/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /próximo mês/i })).toBeInTheDocument();
  });
});
