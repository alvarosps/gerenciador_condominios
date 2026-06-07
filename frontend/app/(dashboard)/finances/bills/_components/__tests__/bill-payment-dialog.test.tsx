import { describe, it, expect, vi, beforeAll, beforeEach, afterEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import { renderWithProviders } from '@/tests/test-utils';
import { BillPaymentDialog } from '../bill-payment-dialog';
import * as billHooks from '@/lib/api/hooks/use-bills';
import * as errorHandler from '@/lib/utils/error-handler';

vi.mock('@/lib/api/hooks/use-bills', async (importOriginal) => {
  const actual = await importOriginal<typeof billHooks>();
  return { ...actual, usePayBill: vi.fn() };
});

// happy-dom is missing the pointer-capture / scroll APIs Radix Select relies on.
// Polyfill the environment boundary so the Select dropdown can be driven in tests.
beforeAll(() => {
  if (!Element.prototype.hasPointerCapture) {
    Element.prototype.hasPointerCapture = () => false;
    Element.prototype.setPointerCapture = () => undefined;
    Element.prototype.releasePointerCapture = () => undefined;
  }
  if (!Element.prototype.scrollIntoView) {
    Element.prototype.scrollIntoView = () => undefined;
  }
});

interface MutateCall {
  request: billHooks.PayBillRequest;
  options?: {
    onSuccess?: () => void;
    onError?: (error: unknown) => void;
  };
}

function makePayBill(behavior: 'success' | 'error') {
  const calls: MutateCall[] = [];
  const mutate = vi.fn((request: billHooks.PayBillRequest, options?: MutateCall['options']) => {
    calls.push({ request, options });
    if (behavior === 'success') options?.onSuccess?.();
    else options?.onError?.(new Error('boom'));
  });
  return { calls, mutation: { mutate, isPending: false } };
}

function submit() {
  return userEvent.click(screen.getByRole('button', { name: /^pagar$/i }));
}

describe('BillPaymentDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('submits without amount (pays the total) with funded_from default caixa', async () => {
    const { calls, mutation } = makePayBill('success');
    vi.mocked(billHooks.usePayBill).mockReturnValue(mutation as never);

    renderWithProviders(
      <BillPaymentDialog open billId={7} amountRemaining={350} onClose={vi.fn()} />,
    );

    await submit();

    await waitFor(() => {
      expect(calls).toHaveLength(1);
    });
    const request = calls[0]?.request;
    expect(request).toBeDefined();
    expect(request?.bill_id).toBe(7);
    expect(request?.funded_from).toBe('caixa');
    expect(request).not.toHaveProperty('amount');
  });

  it('submits a partial amount when filled', async () => {
    const { calls, mutation } = makePayBill('success');
    vi.mocked(billHooks.usePayBill).mockReturnValue(mutation as never);

    renderWithProviders(
      <BillPaymentDialog open billId={7} amountRemaining={350} onClose={vi.fn()} />,
    );

    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '100' } });
    await submit();

    await waitFor(() => {
      expect(calls).toHaveLength(1);
    });
    expect(calls[0]?.request).toMatchObject({
      bill_id: 7,
      amount: 100,
      funded_from: 'caixa',
    });
  });

  it('sends funded_from reserve and shows the reserve notice when reserve is selected', async () => {
    const { calls, mutation } = makePayBill('success');
    vi.mocked(billHooks.usePayBill).mockReturnValue(mutation as never);

    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderWithProviders(
      <BillPaymentDialog open billId={7} amountRemaining={350} onClose={vi.fn()} />,
    );

    await user.click(screen.getByRole('combobox'));
    await user.click(await screen.findByRole('option', { name: 'Reserva' }));

    expect(await screen.findByText(/sairá da reserva/i)).toBeInTheDocument();

    await submit();

    await waitFor(() => {
      expect(calls).toHaveLength(1);
    });
    expect(calls[0]?.request.funded_from).toBe('reserve');
  });

  it('shows a success toast and closes on success', async () => {
    const { mutation } = makePayBill('success');
    vi.mocked(billHooks.usePayBill).mockReturnValue(mutation as never);
    const onClose = vi.fn();

    renderWithProviders(
      <BillPaymentDialog open billId={7} amountRemaining={350} onClose={onClose} />,
    );

    await submit();

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalled();
    });
    expect(onClose).toHaveBeenCalled();
  });

  it('calls handleError on failure', async () => {
    const { mutation } = makePayBill('error');
    vi.mocked(billHooks.usePayBill).mockReturnValue(mutation as never);
    const handleErrorSpy = vi.spyOn(errorHandler, 'handleError').mockImplementation(() => undefined);

    renderWithProviders(
      <BillPaymentDialog open billId={7} amountRemaining={350} onClose={vi.fn()} />,
    );

    await submit();

    await waitFor(() => {
      expect(handleErrorSpy).toHaveBeenCalledWith(expect.anything(), 'Erro ao pagar conta');
    });
  });

  it('does not import useQueryClient (invalidation lives in the S39 hook)', () => {
    const source = readFileSync(
      join(process.cwd(), 'app/(dashboard)/finances/bills/_components/bill-payment-dialog.tsx'),
      'utf-8',
    );
    expect(source).not.toContain('useQueryClient');
    expect(source).not.toContain('invalidateQueries');
  });
});
