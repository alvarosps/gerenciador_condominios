import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockBill, createMockPersonSimple } from '@/tests/mocks/data/finances';
import { ThirdPartyPurchaseDialog } from '../third-party-purchase-dialog';

// Real useCreateThirdPartyPurchase against MSW (POST /finances/bills/create_purchase/) — no hook
// is mocked. `toast` is the global sonner mock from tests/setup.ts.
const API_BASE = 'http://localhost:8008/api';

interface PurchaseBody {
  person_id: number;
  description: string;
  amount: string;
  competence_month: string;
  due_date: string;
  installment_count?: number;
  category_id?: number;
  building_id?: number;
}

function spyPurchase(installments = 1) {
  const bodies: PurchaseBody[] = [];
  server.use(
    http.post(`${API_BASE}/finances/bills/create_purchase/`, async ({ request }) => {
      const body = (await request.json()) as PurchaseBody;
      bodies.push(body);
      return HttpResponse.json(
        Array.from({ length: installments }, (_, index) =>
          createMockBill({
            id: 100 + index,
            description: body.description,
            payment_status: 'paid',
            amount_remaining: '0.00',
            paid_by_person: createMockPersonSimple({ id: body.person_id }),
          })
        ),
        { status: 201 }
      );
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

async function fillRequiredFields(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole('combobox', { name: /quem comprou/i }));
  await user.click(await screen.findByRole('option', { name: 'Rodrigo Souza' }));
  await user.type(screen.getByLabelText(/descrição/i), 'Bomba d’água');
  await user.type(screen.getByLabelText(/valor total/i), '900');
}

describe('ThirdPartyPurchaseDialog', () => {
  beforeEach(() => {
    vi.mocked(toast.success).mockReset();
  });

  it('states plainly that the purchase is already paid and becomes a debt with the person', async () => {
    renderWithProviders(
      <ThirdPartyPurchaseDialog open onClose={() => undefined} year={2026} month={7} />
    );

    expect(
      await screen.findByText(/a compra já foi paga pela pessoa e entra como dívida com ela/i)
    ).toBeInTheDocument();
  });

  it('posts the purchase payload with the board competence and closes on success', async () => {
    const bodies = spyPurchase();
    const onClose = vi.fn();
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    const { queryClient } = renderWithProviders(
      <ThirdPartyPurchaseDialog open onClose={onClose} year={2026} month={7} />
    );

    await fillRequiredFields(user);
    await user.click(screen.getByRole('button', { name: /registrar compra/i }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({
      person_id: 1,
      description: 'Bomba d’água',
      // A decimal STRING — the front never turns money into a float on the way out.
      amount: '900',
      competence_month: '2026-07-01',
      installment_count: 1,
    });
    // Optional fields are omitted rather than sent as null.
    expect(bodies[0]).not.toHaveProperty('category_id');
    expect(bodies[0]).not.toHaveProperty('building_id');

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(toast.success).toHaveBeenCalledWith('Compra registrada com sucesso');

    await waitForQueriesToSettle(queryClient);
  });

  it('sends installment_count and reports how many parcelas the backend created', async () => {
    const bodies = spyPurchase(3);
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    const { queryClient } = renderWithProviders(
      <ThirdPartyPurchaseDialog open onClose={() => undefined} year={2026} month={7} />
    );

    await fillRequiredFields(user);
    const parcelas = screen.getByLabelText(/parcelas/i);
    await user.clear(parcelas);
    await user.type(parcelas, '3');
    await user.click(screen.getByRole('button', { name: /registrar compra/i }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({ installment_count: 3 });
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Compra lançada em 3 parcelas');
    });

    await waitForQueriesToSettle(queryClient);
  });

  it('blocks the submit with a PT message when no person is chosen', async () => {
    const bodies = spyPurchase();
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    renderWithProviders(
      <ThirdPartyPurchaseDialog open onClose={() => undefined} year={2026} month={7} />
    );

    await user.type(await screen.findByLabelText(/descrição/i), 'Bomba');
    await user.type(screen.getByLabelText(/valor total/i), '900');
    await user.click(screen.getByRole('button', { name: /registrar compra/i }));

    expect(await screen.findByText(/pessoa é obrigatória/i)).toBeInTheDocument();
    expect(bodies).toHaveLength(0);
  });

  it('surfaces a backend 400 as a PT toast', async () => {
    server.use(
      http.post(`${API_BASE}/finances/bills/create_purchase/`, () =>
        HttpResponse.json({ error: 'Mês 07/2026 está fechado.' }, { status: 400 })
      )
    );
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    const { queryClient } = renderWithProviders(
      <ThirdPartyPurchaseDialog open onClose={() => undefined} year={2026} month={7} />
    );

    await fillRequiredFields(user);
    await user.click(screen.getByRole('button', { name: /registrar compra/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalled();
    });

    await waitForQueriesToSettle(queryClient);
  });
});
