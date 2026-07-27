import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockBill } from '@/tests/mocks/data/finances';
import { getTodayLocalISO } from '@/lib/utils/formatters';
import { BillPayPopover } from '../bill-pay-popover';
import type { Bill } from '@/lib/schemas/finances/bill.schema';

// The popover is exercised through the real usePayBill mutation hitting MSW (POST
// /finances/bills/:id/pay/) — no hook is mocked. Each submission is spied via an MSW
// request-body capture. `toast` is the global sonner mock from tests/setup.ts.
const API_BASE = 'http://localhost:8008/api';

interface PayBody {
  payment_date: string;
  amount?: number;
  funded_from: string;
  new_total?: string;
  paid_by_person_id?: number;
}

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

function estimatedBill(overrides: Partial<Bill> = {}): Bill {
  return {
    ...createMockBill({
      id: 7,
      amount_is_estimated: true,
      amount_total: '200.00',
      amount_remaining: '200.00',
    }),
    ...overrides,
  } as Bill;
}

function confirmedBill(overrides: Partial<Bill> = {}): Bill {
  return {
    ...createMockBill({
      id: 7,
      amount_is_estimated: false,
      amount_total: '100.00',
      amount_remaining: '60.00',
    }),
    ...overrides,
  } as Bill;
}

async function openPopover() {
  const user = userEvent.setup({ pointerEventsCheck: 0 });
  await user.click(screen.getByRole('button', { name: /^pagar$/i }));
  return user;
}

describe('BillPayPopover', () => {
  beforeEach(() => {
    vi.mocked(toast.success).mockReset();
    vi.mocked(toast.error).mockReset();
  });

  it('pays the full remainder with today as default date when amount is left empty', async () => {
    const bodies = spyPay();
    const bill = confirmedBill();

    const { queryClient } = renderWithProviders(<BillPayPopover bill={bill} />);
    await openPopover();

    await userEvent.click(screen.getByRole('button', { name: /confirmar pagamento/i }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    const body = bodies[0];
    expect(body).toMatchObject({
      bill_id: 7,
      payment_date: getTodayLocalISO(),
      funded_from: 'caixa',
    });
    expect(body).not.toHaveProperty('amount');
    expect(body).not.toHaveProperty('new_total');

    await waitForQueriesToSettle(queryClient);
  });

  it('sends new_total when paying an estimated bill with a value different from the remainder', async () => {
    const bodies = spyPay();
    const bill = estimatedBill({ amount_total: 200, amount_remaining: 200 } as Partial<Bill>);

    const { queryClient } = renderWithProviders(<BillPayPopover bill={bill} />);
    await openPopover();

    fireEvent.change(screen.getByLabelText(/valor/i), { target: { value: '230' } });
    await userEvent.click(screen.getByRole('button', { name: /confirmar pagamento/i }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({ bill_id: 7, amount: 230, new_total: '230.00' });

    await waitForQueriesToSettle(queryClient);
  });

  it('does not send new_total when an estimated bill is paid at exactly the remainder', async () => {
    const bodies = spyPay();
    const bill = estimatedBill({ amount_total: 200, amount_remaining: 200 } as Partial<Bill>);

    const { queryClient } = renderWithProviders(<BillPayPopover bill={bill} />);
    await openPopover();

    fireEvent.change(screen.getByLabelText(/valor/i), { target: { value: '200' } });
    await userEvent.click(screen.getByRole('button', { name: /confirmar pagamento/i }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({ bill_id: 7, amount: 200 });
    expect(bodies[0]).not.toHaveProperty('new_total');

    await waitForQueriesToSettle(queryClient);
  });

  it('shows the juros/multa checkbox only when a confirmed bill gets a value above the remainder', async () => {
    const bill = confirmedBill({ amount_total: 100, amount_remaining: 60 } as Partial<Bill>);

    renderWithProviders(<BillPayPopover bill={bill} />);
    await openPopover();

    expect(screen.queryByText(/adicionar diferença como juros\/multa/i)).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/valor/i), { target: { value: '75' } });

    expect(await screen.findByText(/adicionar diferença como juros\/multa/i)).toBeInTheDocument();
  });

  it('sends new_total = amount_total + (valor - resto) when the checkbox is checked', async () => {
    const bodies = spyPay();
    const bill = confirmedBill({ amount_total: 100, amount_remaining: 60 } as Partial<Bill>);

    const { queryClient } = renderWithProviders(<BillPayPopover bill={bill} />);
    await openPopover();

    fireEvent.change(screen.getByLabelText(/valor/i), { target: { value: '75' } });
    const checkbox = await screen.findByRole('checkbox', {
      name: /adicionar diferença como juros\/multa/i,
    });
    await userEvent.click(checkbox);
    await userEvent.click(screen.getByRole('button', { name: /confirmar pagamento/i }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({ bill_id: 7, amount: 75, new_total: '115.00' });

    await waitForQueriesToSettle(queryClient);
  });

  it('blocks submit with a PT message when value exceeds remainder and the checkbox is unchecked', async () => {
    const bodies = spyPay();
    const bill = confirmedBill({ amount_total: 100, amount_remaining: 60 } as Partial<Bill>);

    renderWithProviders(<BillPayPopover bill={bill} />);
    await openPopover();

    fireEvent.change(screen.getByLabelText(/valor/i), { target: { value: '75' } });
    await userEvent.click(screen.getByRole('button', { name: /confirmar pagamento/i }));

    expect(
      await screen.findByText(
        /o valor excede o restante\. marque a opção de juros\/multa ou reduza o valor\./i
      )
    ).toBeInTheDocument();
    expect(bodies).toHaveLength(0);
  });

  it('sends a plain partial payment (no new_total) when value is below the remainder', async () => {
    const bodies = spyPay();
    const bill = confirmedBill({ amount_total: 100, amount_remaining: 60 } as Partial<Bill>);

    const { queryClient } = renderWithProviders(<BillPayPopover bill={bill} />);
    await openPopover();

    fireEvent.change(screen.getByLabelText(/valor/i), { target: { value: '30' } });
    await userEvent.click(screen.getByRole('button', { name: /confirmar pagamento/i }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({ bill_id: 7, amount: 30 });
    expect(bodies[0]).not.toHaveProperty('new_total');

    await waitForQueriesToSettle(queryClient);
  });

  describe('origem "Terceiro" (S82)', () => {
    async function chooseThirdParty(user: ReturnType<typeof userEvent.setup>) {
      await user.click(screen.getByRole('combobox', { name: /origem/i }));
      await user.click(await screen.findByRole('option', { name: 'Terceiro' }));
    }

    it('reveals the person selector only after "Terceiro" is chosen', async () => {
      renderWithProviders(<BillPayPopover bill={confirmedBill()} />);
      const user = await openPopover();

      expect(screen.queryByText(/quem pagou/i)).not.toBeInTheDocument();

      await chooseThirdParty(user);

      expect(await screen.findByText(/quem pagou/i)).toBeInTheDocument();
      expect(
        screen.getByText(/não sai do caixa: a conta é quitada e vira dívida com essa pessoa\./i)
      ).toBeInTheDocument();
    });

    it('keeps the confirm button disabled until a person is picked', async () => {
      const bodies = spyPay();
      renderWithProviders(<BillPayPopover bill={confirmedBill()} />);
      const user = await openPopover();
      await chooseThirdParty(user);

      const confirm = screen.getByRole('button', { name: /confirmar pagamento/i });
      await waitFor(() => expect(confirm).toBeDisabled());
      expect(bodies).toHaveLength(0);

      await user.click(screen.getByRole('combobox', { name: /quem pagou/i }));
      await user.click(await screen.findByRole('option', { name: 'Rodrigo Souza' }));

      await waitFor(() => expect(confirm).toBeEnabled());
    });

    it('sends funded_from=third_party with the chosen paid_by_person_id', async () => {
      const bodies = spyPay();
      const { queryClient } = renderWithProviders(<BillPayPopover bill={confirmedBill()} />);
      const user = await openPopover();
      await chooseThirdParty(user);

      await user.click(screen.getByRole('combobox', { name: /quem pagou/i }));
      await user.click(await screen.findByRole('option', { name: 'Rodrigo Souza' }));
      await user.click(screen.getByRole('button', { name: /confirmar pagamento/i }));

      await waitFor(() => expect(bodies).toHaveLength(1));
      expect(bodies[0]).toMatchObject({
        bill_id: 7,
        funded_from: 'third_party',
        paid_by_person_id: 1,
      });

      await waitForQueriesToSettle(queryClient);
    });

    it('never sends paid_by_person_id when the source is caixa', async () => {
      const bodies = spyPay();
      const { queryClient } = renderWithProviders(<BillPayPopover bill={confirmedBill()} />);
      await openPopover();

      await userEvent.click(screen.getByRole('button', { name: /confirmar pagamento/i }));

      await waitFor(() => expect(bodies).toHaveLength(1));
      expect(bodies[0]).toMatchObject({ funded_from: 'caixa' });
      expect(bodies[0]).not.toHaveProperty('paid_by_person_id');

      await waitForQueriesToSettle(queryClient);
    });

    it('surfaces a backend 400 on a third-party payment as a PT toast', async () => {
      server.use(
        http.post(`${API_BASE}/finances/bills/7/pay/`, () =>
          HttpResponse.json(
            { error: 'Pagamento de terceiro exige informar quem pagou.' },
            { status: 400 }
          )
        )
      );
      const { queryClient } = renderWithProviders(<BillPayPopover bill={confirmedBill()} />);
      const user = await openPopover();
      await chooseThirdParty(user);
      await user.click(screen.getByRole('combobox', { name: /quem pagou/i }));
      await user.click(await screen.findByRole('option', { name: 'Rodrigo Souza' }));
      await user.click(screen.getByRole('button', { name: /confirmar pagamento/i }));

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          'Pagamento de terceiro exige informar quem pagou.'
        );
      });

      await waitForQueriesToSettle(queryClient);
    });
  });

  it('surfaces the backend 400 message via toast on error', async () => {
    server.use(
      http.post(`${API_BASE}/finances/bills/7/pay/`, () =>
        HttpResponse.json({ error: 'Saldo insuficiente na reserva.' }, { status: 400 })
      )
    );
    const bill = confirmedBill();

    const { queryClient } = renderWithProviders(<BillPayPopover bill={bill} />);
    await openPopover();

    await userEvent.click(screen.getByRole('button', { name: /confirmar pagamento/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Saldo insuficiente na reserva.');
    });

    await waitForQueriesToSettle(queryClient);
  });
});
