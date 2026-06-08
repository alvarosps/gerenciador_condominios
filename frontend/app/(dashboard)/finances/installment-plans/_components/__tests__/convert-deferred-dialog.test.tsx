import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import { renderWithProviders } from '@/tests/test-utils';
import { ConvertDeferredDialog } from '../convert-deferred-dialog';

const convertMutate = vi.fn();

vi.mock('@/lib/api/hooks/use-installment-plans', () => ({
  useConvertDeferred: () => ({ mutate: convertMutate, isPending: false }),
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

beforeEach(() => {
  convertMutate.mockClear();
  vi.mocked(toast.success).mockClear();
});

describe('ConvertDeferredDialog', () => {
  it('shows the "valor preservado" note (the FE never sums the total)', () => {
    renderWithProviders(
      <ConvertDeferredDialog open billId={42} description="IPTU 2026" onClose={vi.fn()} />,
    );
    expect(screen.getByText(/o valor total é preservado/i)).toBeInTheDocument();
  });

  it('submits convert with bill_id + params and toasts on success', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    convertMutate.mockImplementation(
      (_params: unknown, opts?: { onSuccess?: () => void }) => opts?.onSuccess?.(),
    );

    renderWithProviders(
      <ConvertDeferredDialog open billId={42} description="IPTU 2026" onClose={onClose} />,
    );

    await user.click(screen.getByRole('button', { name: 'Converter' }));

    await waitFor(() => expect(convertMutate).toHaveBeenCalledTimes(1));
    const [params] = convertMutate.mock.calls[0] as [Record<string, unknown>];
    expect(params).toMatchObject({
      bill_id: 42,
      installment_count: 3,
      default_due_day: 10,
    });
    expect(toast.success).toHaveBeenCalledWith(
      'Plano de parcelas criado a partir do item adiado',
    );
    expect(onClose).toHaveBeenCalled();
  });

  it('does not submit when billId is null', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <ConvertDeferredDialog open billId={null} description="IPTU 2026" onClose={vi.fn()} />,
    );
    await user.click(screen.getByRole('button', { name: 'Converter' }));
    expect(convertMutate).not.toHaveBeenCalled();
  });
});
