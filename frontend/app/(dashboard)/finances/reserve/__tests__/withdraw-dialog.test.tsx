import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { WithdrawDialog } from '../_components/withdraw-dialog';
import { createMockReserve } from '@/tests/mocks/data/finances';
import type * as reserveHooks from '@/lib/api/hooks/use-reserves';

type WithdrawResult = ReturnType<typeof reserveHooks.useWithdrawReserve>;

const { mockUseWithdrawReserve, mockMutateAsync } = vi.hoisted(() => ({
  mockUseWithdrawReserve: vi.fn<() => WithdrawResult>(),
  mockMutateAsync: vi.fn(),
}));

vi.mock('@/lib/api/hooks/use-reserves', () => ({
  useWithdrawReserve: mockUseWithdrawReserve,
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { toast } from 'sonner';

function submitDialogForm() {
  const formEl = screen.getByRole('dialog').querySelector('form');
  if (!formEl) throw new Error('dialog form not found');
  fireEvent.submit(formEl);
}

const idle = { isPending: false } as const;

describe('WithdrawDialog', () => {
  beforeEach(() => {
    mockMutateAsync.mockReset().mockResolvedValue(createMockReserve());
    mockUseWithdrawReserve.mockReturnValue({
      ...idle,
      mutateAsync: mockMutateAsync,
    } as unknown as WithdrawResult);
    vi.mocked(toast.success).mockReset();
    vi.mocked(toast.error).mockReset();
  });

  it('submits a valid amount and calls withdraw with { reserveId, payload }, then closes', async () => {
    const onClose = vi.fn();
    renderWithProviders(
      <WithdrawDialog open reserve={createMockReserve({ id: 5, balance: 1000 })} onClose={onClose} />,
    );
    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '300' } });
    submitDialogForm();
    await waitFor(() => expect(mockMutateAsync).toHaveBeenCalled());
    expect(mockMutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({ reserveId: 5, payload: expect.objectContaining({ amount: 300 }) }),
    );
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(toast.success).toHaveBeenCalled();
  });

  it('blocks submission when amount <= 0 (Zod, PT) — mutation not called', async () => {
    renderWithProviders(<WithdrawDialog open reserve={createMockReserve()} onClose={vi.fn()} />);
    submitDialogForm();
    expect(await screen.findByText(/maior que zero/i)).toBeInTheDocument();
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it('shows the backend insufficient-balance PT error — the front never simulates the balance', async () => {
    mockMutateAsync.mockRejectedValueOnce(
      Object.assign(new Error('request failed'), {
        isAxiosError: true,
        response: { status: 400, data: { error: 'Saldo da reserva insuficiente.' } },
      }),
    );
    renderWithProviders(
      <WithdrawDialog open reserve={createMockReserve({ id: 5, balance: 100 })} onClose={vi.fn()} />,
    );
    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '999' } });
    submitDialogForm();
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Saldo da reserva insuficiente.'));
  });
});
