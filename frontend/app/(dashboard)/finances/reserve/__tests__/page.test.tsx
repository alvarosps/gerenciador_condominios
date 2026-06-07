import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, createTestQueryClient } from '@/tests/test-utils';
import ReservePage from '../page';
import { createMockReserve } from '@/tests/mocks/data/finances';
import type * as reserveHooks from '@/lib/api/hooks/use-reserves';
import type * as movementHooks from '@/lib/api/hooks/use-reserve-movements';
import type * as authStore from '@/store/auth-store';

type ReservesResult = ReturnType<typeof reserveHooks.useReserves>;
type MovementsResult = ReturnType<typeof movementHooks.useReserveMovements>;
type AuthStoreResult = ReturnType<typeof authStore.useAuthStore>;
type DepositResult = ReturnType<typeof reserveHooks.useDepositReserve>;
type WithdrawResult = ReturnType<typeof reserveHooks.useWithdrawReserve>;

// Use vi.hoisted so mock variables are available when vi.mock factories run
const {
  mockUseReserves,
  mockUseReserveMovements,
  mockUseDepositReserve,
  mockUseWithdrawReserve,
  mockUseAuthStore,
} = vi.hoisted(() => ({
  mockUseReserves: vi.fn<() => ReservesResult>(),
  mockUseReserveMovements: vi.fn<() => MovementsResult>(),
  mockUseDepositReserve: vi.fn<() => DepositResult>(),
  mockUseWithdrawReserve: vi.fn<() => WithdrawResult>(),
  mockUseAuthStore: vi.fn<() => AuthStoreResult>(),
}));

vi.mock('@/lib/api/hooks/use-reserves', () => ({
  useReserves: mockUseReserves,
  useDepositReserve: mockUseDepositReserve,
  useWithdrawReserve: mockUseWithdrawReserve,
  useReserve: () => ({ data: null, isLoading: false }),
  useCreateReserve: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateReserve: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteReserve: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock('@/lib/api/hooks/use-reserve-movements', () => ({
  useReserveMovements: mockUseReserveMovements,
}));
vi.mock('@/store/auth-store', () => ({
  useAuthStore: mockUseAuthStore,
}));

const idleMutation = {
  mutateAsync: vi.fn(),
  isPending: false,
  isError: false,
  isSuccess: false,
} as const;

describe('ReservePage', () => {
  beforeEach(() => {
    mockUseReserves.mockReset();
    mockUseReserveMovements.mockReset();
    mockUseDepositReserve.mockReturnValue({ ...idleMutation } as unknown as DepositResult);
    mockUseWithdrawReserve.mockReturnValue({ ...idleMutation } as unknown as WithdrawResult);
  });

  it('renders reserve balance cards for staff', async () => {
    mockUseAuthStore.mockReturnValue({ user: { is_staff: true } } as unknown);
    mockUseReserves.mockReturnValue({
      isLoading: false,
      error: null,
      data: [createMockReserve({ id: 1, name: 'Emergência', balance: 5000 })],
    } as unknown as ReservesResult);
    mockUseReserveMovements.mockReturnValue({ isLoading: false, data: [] } as unknown as MovementsResult);

    renderWithProviders(<ReservePage />, { queryClient: createTestQueryClient() });

    await waitFor(() => {
      expect(screen.getByText('Emergência')).toBeInTheDocument();
    });

    // Staff sees deposit/withdraw buttons
    expect(screen.getByRole('button', { name: /Depositar/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sacar/i })).toBeInTheDocument();
  });

  it('hides deposit/withdraw buttons for non-staff', async () => {
    mockUseAuthStore.mockReturnValue({ user: { is_staff: false } } as unknown);
    mockUseReserves.mockReturnValue({
      isLoading: false,
      error: null,
      data: [createMockReserve()],
    } as unknown as ReservesResult);
    mockUseReserveMovements.mockReturnValue({ isLoading: false, data: [] } as unknown as MovementsResult);

    renderWithProviders(<ReservePage />, { queryClient: createTestQueryClient() });

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /Depositar/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Sacar/i })).not.toBeInTheDocument();
    });
  });

  it('shows deposit dialog when deposit button clicked', async () => {
    mockUseAuthStore.mockReturnValue({ user: { is_staff: true } } as unknown);
    mockUseReserves.mockReturnValue({
      isLoading: false,
      error: null,
      data: [createMockReserve({ id: 1, name: 'Fundo' })],
    } as unknown as ReservesResult);
    mockUseReserveMovements.mockReturnValue({ isLoading: false, data: [] } as unknown as MovementsResult);

    renderWithProviders(<ReservePage />, { queryClient: createTestQueryClient() });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Depositar/i })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: /Depositar/i }));

    await waitFor(() => {
      expect(screen.getByText(/Depositar em Fundo/i)).toBeInTheDocument();
    });
  });

  it('renders movements table', async () => {
    mockUseAuthStore.mockReturnValue({ user: { is_staff: false } } as unknown);
    mockUseReserves.mockReturnValue({ isLoading: false, error: null, data: [] } as unknown as ReservesResult);
    mockUseReserveMovements.mockReturnValue({
      isLoading: false,
      data: [
        { id: 1, reserve: { id: 1, name: 'ER' }, kind: 'deposit' as const, amount: 1000, movement_date: '2026-06-01', bill: null, reference: null, notes: null },
      ],
    } as unknown as MovementsResult);

    renderWithProviders(<ReservePage />, { queryClient: createTestQueryClient() });

    await waitFor(() => {
      expect(screen.getByText('Movimentações')).toBeInTheDocument();
    });
  });
});
