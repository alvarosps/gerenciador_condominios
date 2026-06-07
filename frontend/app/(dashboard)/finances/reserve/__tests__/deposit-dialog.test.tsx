import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { DepositDialog } from '../_components/deposit-dialog';
import { createMockReserve } from '@/tests/mocks/data/finances';
import type * as reserveHooks from '@/lib/api/hooks/use-reserves';

type DepositResult = ReturnType<typeof reserveHooks.useDepositReserve>;

const { mockUseDepositReserve, mockMutateAsync } = vi.hoisted(() => ({
  mockUseDepositReserve: vi.fn<() => DepositResult>(),
  mockMutateAsync: vi.fn(),
}));

vi.mock('@/lib/api/hooks/use-reserves', () => ({
  useDepositReserve: mockUseDepositReserve,
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { toast } from 'sonner';

// Radix Dialog forms must be submitted via the form element (happy-dom does not translate a
// submit-button click into a form submit) — the project's established pattern.
function submitDialogForm() {
  const formEl = screen.getByRole('dialog').querySelector('form');
  if (!formEl) throw new Error('dialog form not found');
  fireEvent.submit(formEl);
}

const idle = { isPending: false } as const;

describe('DepositDialog', () => {
  beforeEach(() => {
    mockMutateAsync.mockReset().mockResolvedValue(createMockReserve());
    mockUseDepositReserve.mockReturnValue({
      ...idle,
      mutateAsync: mockMutateAsync,
    } as unknown as DepositResult);
    vi.mocked(toast.success).mockReset();
    vi.mocked(toast.error).mockReset();
  });

  it('submits a valid amount and calls deposit with { reserveId, payload }, then closes', async () => {
    const onClose = vi.fn();
    renderWithProviders(
      <DepositDialog open reserve={createMockReserve({ id: 3 })} onClose={onClose} />,
    );
    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '250' } });
    submitDialogForm();
    await waitFor(() => expect(mockMutateAsync).toHaveBeenCalled());
    expect(mockMutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({ reserveId: 3, payload: expect.objectContaining({ amount: 250 }) }),
    );
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(toast.success).toHaveBeenCalled();
  });

  it('blocks submission when amount <= 0 (Zod, PT) — mutation not called', async () => {
    renderWithProviders(<DepositDialog open reserve={createMockReserve()} onClose={vi.fn()} />);
    submitDialogForm();
    expect(await screen.findByText(/maior que zero/i)).toBeInTheDocument();
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it('shows the server PT error on rejection (does not simulate balance)', async () => {
    mockMutateAsync.mockRejectedValueOnce(
      Object.assign(new Error('request failed'), {
        isAxiosError: true,
        response: { status: 400, data: { error: 'Erro do servidor.' } },
      }),
    );
    renderWithProviders(<DepositDialog open reserve={createMockReserve({ id: 3 })} onClose={vi.fn()} />);
    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '50' } });
    submitDialogForm();
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Erro do servidor.'));
  });
});
