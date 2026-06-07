import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import { renderWithProviders, createTestQueryClient } from '@/tests/test-utils';
import MonthClosePage from '../page';
import { createMockCondoMonthClose } from '@/tests/mocks/data/finances';
import type * as closeHooks from '@/lib/api/hooks/use-condo-month-closes';
import type * as authStore from '@/store/auth-store';

type CondoMonthClosesResult = ReturnType<typeof closeHooks.useCondoMonthCloses>;
type CloseMonthResult = ReturnType<typeof closeHooks.useCloseMonth>;
type ReopenMonthResult = ReturnType<typeof closeHooks.useReopenMonth>;
type AuthStoreResult = ReturnType<typeof authStore.useAuthStore>;

// Use vi.hoisted so mock variables are available when vi.mock factories run
const {
  mockUseCondoMonthCloses,
  mockUseCloseMonth,
  mockUseReopenMonth,
  mockUseAuthStore,
} = vi.hoisted(() => ({
  mockUseCondoMonthCloses: vi.fn<() => CondoMonthClosesResult>(),
  mockUseCloseMonth: vi.fn<() => CloseMonthResult>(),
  mockUseReopenMonth: vi.fn<() => ReopenMonthResult>(),
  mockUseAuthStore: vi.fn<() => AuthStoreResult>(),
}));

vi.mock('@/lib/api/hooks/use-condo-month-closes', () => ({
  useCondoMonthCloses: mockUseCondoMonthCloses,
  useCondoMonthClose: () => ({ data: null, isLoading: false }),
  useCloseMonth: mockUseCloseMonth,
  useReopenMonth: mockUseReopenMonth,
}));
vi.mock('@/store/auth-store', () => ({
  useAuthStore: mockUseAuthStore,
}));

const idleMutation = {
  mutateAsync: vi.fn(),
  isPending: false,
  isError: false,
  isSuccess: false,
  mutate: vi.fn(),
} as const;

describe('MonthClosePage', () => {
  beforeEach(() => {
    mockUseCondoMonthCloses.mockReset();
    mockUseCloseMonth.mockReturnValue({ ...idleMutation } as unknown as CloseMonthResult);
    mockUseReopenMonth.mockReturnValue({ ...idleMutation } as unknown as ReopenMonthResult);
  });

  it('renders the page title', async () => {
    mockUseAuthStore.mockReturnValue({ user: { is_staff: false } } as unknown);
    mockUseCondoMonthCloses.mockReturnValue({ isLoading: false, error: null, data: [] } as unknown as CondoMonthClosesResult);

    renderWithProviders(<MonthClosePage />, { queryClient: createTestQueryClient() });

    await waitFor(() => {
      expect(screen.getByText('Fechamento Mensal')).toBeInTheDocument();
    });
  });

  it('renders month closes in the table', async () => {
    mockUseAuthStore.mockReturnValue({ user: { is_staff: false } } as unknown);
    mockUseCondoMonthCloses.mockReturnValue({
      isLoading: false,
      error: null,
      data: [
        createMockCondoMonthClose({ id: 1, reference_month: '2026-05-01', status: 'closed' }),
        createMockCondoMonthClose({ id: 2, reference_month: '2026-04-01', status: 'open' }),
      ],
    } as unknown as CondoMonthClosesResult);

    renderWithProviders(<MonthClosePage />, { queryClient: createTestQueryClient() });

    await waitFor(() => {
      // DataTable renders both desktop table and mobile cards views
      expect(screen.getAllByText(/maio de 2026/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/abril de 2026/i).length).toBeGreaterThan(0);
    });
  });

  it('shows "Fechar" button for open months (staff only)', async () => {
    mockUseAuthStore.mockReturnValue({ user: { is_staff: true } } as unknown);
    mockUseCondoMonthCloses.mockReturnValue({
      isLoading: false,
      error: null,
      data: [createMockCondoMonthClose({ id: 1, status: 'open' })],
    } as unknown as CondoMonthClosesResult);

    renderWithProviders(<MonthClosePage />, { queryClient: createTestQueryClient() });

    // DataTable renders both desktop and mobile views — use getAllByRole
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /Fechar mês/i }).length).toBeGreaterThan(0);
    });
  });

  it('shows "Reabrir" button for closed months (staff only)', async () => {
    mockUseAuthStore.mockReturnValue({ user: { is_staff: true } } as unknown);
    mockUseCondoMonthCloses.mockReturnValue({
      isLoading: false,
      error: null,
      data: [createMockCondoMonthClose({ id: 1, status: 'closed' })],
    } as unknown as CondoMonthClosesResult);

    renderWithProviders(<MonthClosePage />, { queryClient: createTestQueryClient() });

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /Reabrir mês/i }).length).toBeGreaterThan(0);
    });
  });

  it('hides action buttons for non-staff', async () => {
    mockUseAuthStore.mockReturnValue({ user: { is_staff: false } } as unknown);
    mockUseCondoMonthCloses.mockReturnValue({
      isLoading: false,
      error: null,
      data: [
        createMockCondoMonthClose({ id: 1, status: 'open' }),
        createMockCondoMonthClose({ id: 2, status: 'closed' }),
      ],
    } as unknown as CondoMonthClosesResult);

    renderWithProviders(<MonthClosePage />, { queryClient: createTestQueryClient() });

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /Fechar mês/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Reabrir mês/i })).not.toBeInTheDocument();
    });
  });

  it('opens confirm dialog when clicking close', async () => {
    mockUseAuthStore.mockReturnValue({ user: { is_staff: true } } as unknown);
    mockUseCondoMonthCloses.mockReturnValue({
      isLoading: false,
      error: null,
      data: [createMockCondoMonthClose({ id: 1, reference_month: '2026-05-01', status: 'open' })],
    } as unknown as CondoMonthClosesResult);

    renderWithProviders(<MonthClosePage />, { queryClient: createTestQueryClient() });

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /Fechar mês/i }).length).toBeGreaterThan(0);
    });

    // Click the first instance (both desktop and mobile render the button)
    const [firstButton] = screen.getAllByRole('button', { name: /Fechar mês/i });
    if (!firstButton) throw new Error('Fechar mês button not found');
    fireEvent.click(firstButton);

    await waitFor(() => {
      expect(screen.getByText(/Fechar o mês congela/i)).toBeInTheDocument();
    });
  });
});
