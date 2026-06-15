import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { http, HttpResponse } from 'msw';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockBill } from '@/tests/mocks/data/finances';
import { BillPaymentDialog } from '../bill-payment-dialog';

// The payment is exercised through the real usePayBill mutation hitting MSW (POST
// /finances/bills/:id/pay/) — no hook is mocked. Each submission is spied via an MSW request-body
// capture. `toast` is the global sonner mock from tests/setup.ts.
const API_BASE = 'http://localhost:8008/api';

interface PayBody {
  payment_date: string;
  amount?: number;
  funded_from: string;
}

// Spy the pay request body. The path :id resolves to the bill being paid; captured alongside body.
function spyPay() {
  const bodies: (PayBody & { bill_id: number })[] = [];
  server.use(
    http.post(`${API_BASE}/finances/bills/:id/pay/`, async ({ params, request }) => {
      const body = (await request.json()) as PayBody;
      bodies.push({ ...body, bill_id: Number(params.id) });
      return HttpResponse.json(createMockBill({ id: Number(params.id), payment_status: 'paid' }));
    })
  );
  return bodies;
}

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

function submit() {
  return userEvent.click(screen.getByRole('button', { name: /^pagar$/i }));
}

describe('BillPaymentDialog', () => {
  beforeEach(() => {
    vi.mocked(toast.success).mockReset();
    vi.mocked(toast.error).mockReset();
  });

  it('submits without amount (pays the total) with funded_from default caixa', async () => {
    const bodies = spyPay();

    const { queryClient } = renderWithProviders(
      <BillPaymentDialog open billId={7} amountRemaining={350} onClose={vi.fn()} />
    );

    await submit();

    await waitFor(() => {
      expect(bodies).toHaveLength(1);
    });
    const body = bodies[0];
    expect(body).toBeDefined();
    expect(body?.bill_id).toBe(7);
    expect(body?.funded_from).toBe('caixa');
    expect(body).not.toHaveProperty('amount');

    await waitForQueriesToSettle(queryClient);
  });

  it('submits a partial amount when filled', async () => {
    const bodies = spyPay();

    const { queryClient } = renderWithProviders(
      <BillPaymentDialog open billId={7} amountRemaining={350} onClose={vi.fn()} />
    );

    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '100' } });
    await submit();

    await waitFor(() => {
      expect(bodies).toHaveLength(1);
    });
    expect(bodies[0]).toMatchObject({
      bill_id: 7,
      amount: 100,
      funded_from: 'caixa',
    });

    await waitForQueriesToSettle(queryClient);
  });

  it('sends funded_from reserve and shows the reserve notice when reserve is selected', async () => {
    const bodies = spyPay();

    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const { queryClient } = renderWithProviders(
      <BillPaymentDialog open billId={7} amountRemaining={350} onClose={vi.fn()} />
    );

    await user.click(screen.getByRole('combobox'));
    await user.click(await screen.findByRole('option', { name: 'Reserva' }));

    expect(await screen.findByText(/sairá da reserva/i)).toBeInTheDocument();

    await submit();

    await waitFor(() => {
      expect(bodies).toHaveLength(1);
    });
    expect(bodies[0]?.funded_from).toBe('reserve');

    await waitForQueriesToSettle(queryClient);
  });

  it('shows a success toast and closes on success', async () => {
    spyPay();
    const onClose = vi.fn();

    const { queryClient } = renderWithProviders(
      <BillPaymentDialog open billId={7} amountRemaining={350} onClose={onClose} />
    );

    await submit();

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalled();
    });
    expect(onClose).toHaveBeenCalled();

    await waitForQueriesToSettle(queryClient);
  });

  it('logs the PT error and does not close on a 400 rejection', async () => {
    // The dialog routes failures through handleError(error, 'Erro ao pagar conta'), which writes
    // the resolved PT message to console.error (the sink) — assert it lands there with the server's
    // PT message; no success toast / onClose side effect should fire. (This console.error is the
    // component's own logging, not an unhandled rejection.)
    server.use(
      http.post(`${API_BASE}/finances/bills/7/pay/`, () =>
        HttpResponse.json({ error: 'Saldo insuficiente na reserva.' }, { status: 400 })
      )
    );
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const onClose = vi.fn();

    const { queryClient } = renderWithProviders(
      <BillPaymentDialog open billId={7} amountRemaining={350} onClose={onClose} />
    );

    await submit();

    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        '[Erro ao pagar conta] Saldo insuficiente na reserva.',
        expect.anything()
      );
    });
    expect(toast.success).not.toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();

    consoleErrorSpy.mockRestore();
    await waitForQueriesToSettle(queryClient);
  });

  it('does not import useQueryClient (invalidation lives in the S39 hook)', () => {
    const source = readFileSync(
      join(process.cwd(), 'app/(dashboard)/finances/bills/_components/bill-payment-dialog.tsx'),
      'utf-8'
    );
    expect(source).not.toContain('useQueryClient');
    expect(source).not.toContain('invalidateQueries');
  });
});
