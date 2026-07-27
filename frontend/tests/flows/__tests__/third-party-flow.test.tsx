/**
 * Third-party debt flow as an integration test (design §9, S82) — MSW is the ONLY boundary: no
 * hook, component, apiClient or TanStack internal is mocked (`next/navigation` is a framework
 * boundary, like the S81 statement-page test).
 *
 *   compra de terceiro → aparece no extrato da pessoa → acerto → o saldo devido baixa
 *
 * The MSW backend is STATEFUL on purpose: it recomputes the statement from the purchases and
 * settlements it has received, exactly as the real FIFO service does at every read (the allocation
 * is never persisted). That is what makes the last step meaningful — the balance drops because the
 * settlement reached the server and the page refetched, not because the test said so.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, renderHook, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { useParams } from 'next/navigation';
import { createTestQueryClient, createWrapper, renderWithProviders } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useCreateThirdPartyPurchase } from '@/lib/api/hooks/use-bills';
import { createMockBill, createMockPersonSimple } from '@/tests/mocks/data/finances';
import ThirdPartyStatementPage from '@/app/(dashboard)/finances/third-party/[id]/page';
import { useAuthStore } from '@/store/auth-store';

// Only next/navigation is stubbed — a framework boundary (no router exists outside Next), never
// an application hook. `useRouter` is needed by the settlement modal's error path.
vi.mock('next/navigation', () => ({
  useParams: vi.fn(() => ({ id: '1' })),
  useRouter: vi.fn(() => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn(), back: vi.fn() })),
}));

const API_BASE = 'http://localhost:8008/api';
const PERSON_ID = 1;
const PURCHASE_AMOUNT = 900;

interface PurchaseBody {
  person_id: number;
  description: string;
  amount: string;
  competence_month: string;
  due_date: string;
  installment_count?: number;
}

interface SettlementBody {
  person_id: number;
  settlement_date: string;
  amount: string;
}

/** Money as the wire carries it: a 2-decimal string, never a float. */
function money(value: number): string {
  return value.toFixed(2);
}

/**
 * Stand-in for the backend: holds the purchases and settlements, and derives the statement the
 * same way the real service does (settlements consumed against what is owed, FIFO by month).
 */
function installStatefulBackend() {
  const purchases: { description: string; amount: number; month: string; date: string }[] = [];
  const settlements: { amount: number; date: string }[] = [];
  const captured: { purchase?: PurchaseBody; settlement?: SettlementBody } = {};

  function buildStatement() {
    const totalDevido = purchases.reduce((sum, purchase) => sum + purchase.amount, 0);
    const totalPago = settlements.reduce((sum, settlement) => sum + settlement.amount, 0);
    // FIFO: the settlement pool drains the months in chronological order.
    let pool = totalPago;
    const months = purchases.map((purchase) => {
      const aplicado = Math.min(pool, purchase.amount);
      pool -= aplicado;
      const resto = purchase.amount - aplicado;
      return {
        month: purchase.month,
        devido: money(purchase.amount),
        aplicado: money(aplicado),
        resto: money(resto),
        status: resto === 0 ? ('paid' as const) : ('open' as const),
        items: [
          {
            kind: 'purchase' as const,
            id: 1,
            description: purchase.description,
            amount: money(purchase.amount),
            date: purchase.date,
          },
        ],
      };
    });
    return {
      person_id: PERSON_ID,
      person_name: 'Rodrigo Souza',
      months,
      totals: {
        total_devido: money(totalDevido),
        total_pago: money(totalPago),
        total_em_aberto: money(Math.max(totalDevido - totalPago, 0)),
        total_atrasado: money(0),
        saldo_credor: money(Math.max(totalPago - totalDevido, 0)),
      },
    };
  }

  server.use(
    http.post(`${API_BASE}/finances/bills/create_purchase/`, async ({ request }) => {
      const body = (await request.json()) as PurchaseBody;
      captured.purchase = body;
      const count = body.installment_count ?? 1;
      // The BACKEND splits a parcelamento — the frontend only forwards the total and the count.
      const per = Number(body.amount) / count;
      const bills = Array.from({ length: count }, (_, index) => {
        purchases.push({
          description: body.description,
          amount: per,
          month: body.competence_month,
          date: body.due_date,
        });
        return createMockBill({
          id: 500 + index,
          description: body.description,
          payment_status: 'paid',
          amount_total: money(per),
          amount_remaining: '0.00',
          paid_by_person: createMockPersonSimple({ id: body.person_id, name: 'Rodrigo Souza' }),
        });
      });
      return HttpResponse.json(bills, { status: 201 });
    }),

    http.get(`${API_BASE}/finances/third-party/statement/`, () =>
      HttpResponse.json(buildStatement())
    ),

    http.post(`${API_BASE}/finances/third-party-settlements/`, async ({ request }) => {
      const body = (await request.json()) as SettlementBody;
      captured.settlement = body;
      settlements.push({ amount: Number(body.amount), date: body.settlement_date });
      return HttpResponse.json(
        {
          id: settlements.length,
          condominium: { id: 1, name: 'Condomínio' },
          person: createMockPersonSimple({ id: body.person_id, name: 'Rodrigo Souza' }),
          settlement_date: body.settlement_date,
          amount: body.amount,
          method: '',
          notes: '',
        },
        { status: 201 }
      );
    })
  );

  return captured;
}

/**
 * Every `text-2xl` on the statement page is a StatCard value, in render order:
 * [Em aberto, Atrasado, Crédito]. Reading the node directly (rather than by text) is what lets the
 * test assert that the FIRST card CHANGED — a `getByText` would happily match the same currency
 * string rendered by a month row and prove nothing.
 */
function statCardValues(): string[] {
  return Array.from(document.querySelectorAll('span.text-2xl')).map((element) =>
    // `formatCurrency` (Intl pt-BR) separates "R$" from the digits with a NON-BREAKING space;
    // normalizing it keeps the expectations readable as plain ASCII.
    (element.textContent ?? '').replace(/ /g, ' ')
  );
}

describe('third-party debt flow (real hooks + page, MSW boundary)', () => {
  beforeEach(() => {
    vi.mocked(useParams).mockReturnValue({ id: String(PERSON_ID) });
    useAuthStore.setState({
      user: { id: 1, email: 'a@b.c', first_name: 'A', last_name: 'B', is_staff: true },
      isAuthenticated: true,
    });
  });

  it('runs compra de terceiro → extrato da pessoa → acerto → saldo devido baixa', async () => {
    const captured = installStatefulBackend();
    const client = createTestQueryClient();
    const wrapper = createWrapper(client);

    // 1. Compra de terceiro — born paid, nothing leaves the caixa.
    const purchase = renderHook(() => useCreateThirdPartyPurchase(), { wrapper });
    let createdBills = 0;
    await act(async () => {
      const bills = await purchase.result.current.mutateAsync({
        person_id: PERSON_ID,
        description: 'Bomba d’água',
        amount: money(PURCHASE_AMOUNT),
        competence_month: '2026-07-01',
        due_date: '2026-07-10',
        installment_count: 1,
      });
      createdBills = bills.length;
    });
    expect(captured.purchase).toMatchObject({
      person_id: PERSON_ID,
      amount: '900.00',
      competence_month: '2026-07-01',
    });
    expect(createdBills).toBe(1);
    // The purchase carries the person, which is what the cockpit badge renders.
    expect(captured.purchase?.description).toBe('Bomba d’água');

    // 2. Extrato da pessoa — the real page renders the debt the purchase created.
    renderWithProviders(<ThirdPartyStatementPage />, { queryClient: client });

    expect(await screen.findByText('Rodrigo Souza')).toBeInTheDocument();
    // "Em aberto" (the first StatCard) = the full purchase: nothing has been settled yet.
    await waitFor(() => {
      expect(statCardValues()[0]).toBe('R$ 900,00');
    });

    // Expanding the month reveals WHICH movement composes it — the purchase just created.
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const detailToggles = await screen.findAllByRole('button', { name: /detalhes de/i });
    const firstToggle = detailToggles[0];
    if (!firstToggle) throw new Error('detail toggle not found');
    await user.click(firstToggle);
    // `findAllByText`, not `findByText`: DataTable renders a desktop table AND a CSS-hidden mobile
    // card view from the same `render`, so every cell string legitimately appears twice.
    expect((await screen.findAllByText('Bomba d’água')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Compra').length).toBeGreaterThan(0);

    // 3. Acerto — partial, through the real "Registrar acerto" modal.
    await user.click(screen.getByRole('button', { name: /registrar acerto/i }));

    const dialog = await screen.findByRole('dialog');
    await user.type(await screen.findByLabelText(/^valor/i), '400');
    await user.click(within(dialog).getByRole('button', { name: /^registrar$/i }));

    await waitFor(() => expect(captured.settlement).toBeDefined());
    expect(captured.settlement).toMatchObject({ person_id: PERSON_ID, amount: '400' });

    // 4. O saldo baixa — the statement refetches (invalidated by the settlement mutation) and the
    // "Em aberto" StatCard drops from 900 to 900-400. The figure is the backend's recomputed
    // total, never a client-side subtraction.
    await waitFor(
      () => {
        expect(statCardValues()[0]).toBe('R$ 500,00');
      },
      { timeout: 5000 }
    );
    // The month row still shows what the purchase COST (devido = 900) — a partial acerto lowers
    // the balance, it does not rewrite history.
    expect(screen.getAllByText('R$ 900,00').length).toBeGreaterThan(0);
  });
});
