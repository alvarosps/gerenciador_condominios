import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, fireEvent, within } from '@testing-library/react';
import { renderWithProviders, createTestQueryClient } from '@/tests/test-utils';
import MonthClosePage from '../page';
import { createMockCondoMonthClose } from '@/tests/mocks/data/finances';
import type * as closeHooks from '@/lib/api/hooks/use-condo-month-closes';
import type * as authStore from '@/store/auth-store';

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
import { toast } from 'sonner';

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

  it('confirming a close derives {year,month} by split, calls mutateAsync and toasts success', async () => {
    vi.mocked(toast.success).mockReset();
    mockUseAuthStore.mockReturnValue({ user: { is_staff: true } } as unknown);
    const mutateAsync = vi.fn().mockResolvedValue(createMockCondoMonthClose());
    mockUseCloseMonth.mockReturnValue({
      ...idleMutation,
      mutateAsync,
    } as unknown as CloseMonthResult);
    mockUseCondoMonthCloses.mockReturnValue({
      isLoading: false,
      error: null,
      data: [createMockCondoMonthClose({ id: 1, reference_month: '2026-05-01', status: 'open' })],
    } as unknown as CondoMonthClosesResult);

    renderWithProviders(<MonthClosePage />, { queryClient: createTestQueryClient() });

    const [openBtn] = await screen.findAllByRole('button', { name: /Fechar mês/i });
    if (!openBtn) throw new Error('open button not found');
    fireEvent.click(openBtn);
    const dialog = await screen.findByRole('alertdialog');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Fechar mês' }));

    // 2026-05-01 → {year:2026, month:5} via split (NOT new Date) — no off-by-one/TZ shift.
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith({ year: 2026, month: 5 }));
    expect(toast.success).toHaveBeenCalledWith('Mês fechado com sucesso');
  });

  it('surfaces the backend PT error (chronological gap) via toast.error on reject', async () => {
    vi.mocked(toast.error).mockReset();
    mockUseAuthStore.mockReturnValue({ user: { is_staff: true } } as unknown);
    const mutateAsync = vi.fn().mockRejectedValue(
      Object.assign(new Error('request failed'), {
        isAxiosError: true,
        response: {
          status: 400,
          data: { error: 'Feche os meses anteriores antes de fechar este mês.' },
        },
      }),
    );
    mockUseCloseMonth.mockReturnValue({
      ...idleMutation,
      mutateAsync,
    } as unknown as CloseMonthResult);
    mockUseCondoMonthCloses.mockReturnValue({
      isLoading: false,
      error: null,
      data: [createMockCondoMonthClose({ id: 1, reference_month: '2026-05-01', status: 'open' })],
    } as unknown as CondoMonthClosesResult);

    renderWithProviders(<MonthClosePage />, { queryClient: createTestQueryClient() });

    const [openBtn] = await screen.findAllByRole('button', { name: /Fechar mês/i });
    if (!openBtn) throw new Error('open button not found');
    fireEvent.click(openBtn);
    const dialog = await screen.findByRole('alertdialog');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Fechar mês' }));

    // The front never validates chronology — it shows the server's PT message verbatim (§18).
    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        'Feche os meses anteriores antes de fechar este mês.',
      ),
    );
  });
});
