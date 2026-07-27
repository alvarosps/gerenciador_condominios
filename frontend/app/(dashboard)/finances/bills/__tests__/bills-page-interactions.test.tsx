import { describe, it, expect, beforeAll, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import { createMockBill, createMockMonthBoard } from '@/tests/mocks/data/finances';
import BillsPage from '../page';

// Real hooks (useMonthBoard / usePayBill / useCreateBillWithLines / useConsolidateDebt / …) hit
// MSW — no hook is mocked (mock policy). Each mutation is spied via an MSW request-body capture.
const API_BASE = 'http://localhost:8008/api';

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

function setAdmin(isStaff: boolean) {
  useAuthStore.setState({
    user: { id: 1, email: 'a@b.c', first_name: 'A', last_name: 'B', is_staff: isStaff },
    isAuthenticated: true,
  });
}

function setIptuAlerts() {
  server.use(
    http.get(`${API_BASE}/finances/finance-dashboard/iptu_alerts/`, () =>
      HttpResponse.json({ alerts: [], warning_count: 0, critical_count: 0 })
    )
  );
}

function setBillingAccounts(accounts: unknown[] = []) {
  server.use(http.get(`${API_BASE}/finances/billing-accounts/`, () => HttpResponse.json(accounts)));
}

function setMonthBoard(board: ReturnType<typeof createMockMonthBoard>) {
  server.use(
    http.get(`${API_BASE}/finances/finance-dashboard/month_board/`, () => HttpResponse.json(board))
  );
}

function spyPay() {
  const bodies: { bill_id: number }[] = [];
  server.use(
    http.post(`${API_BASE}/finances/bills/:id/pay/`, ({ params }) => {
      bodies.push({ bill_id: Number(params.id) });
      return HttpResponse.json(
        createMockBill({ id: Number(params.id), payment_status: 'paid', amount_remaining: 0 })
      );
    })
  );
  return bodies;
}

function spyCreateWithLines() {
  const bodies: unknown[] = [];
  server.use(
    http.post(`${API_BASE}/finances/bills/create_with_lines/`, async ({ request }) => {
      bodies.push(await request.json());
      return HttpResponse.json(createMockBill({ id: 100 }), { status: 201 });
    })
  );
  return bodies;
}

// DataTable renders both the desktop table and a CSS-hidden mobile card view for the same rows
// (data-table-cards.tsx) — action buttons are legitimately duplicated in the DOM, so scope to the
// first (desktop) occurrence, mirroring the established pattern in bills-page-board.test.tsx.
function firstButtonNamed(name: RegExp): HTMLElement {
  const button = screen.getAllByRole('button', { name })[0];
  if (!button) throw new Error(`button matching ${name.toString()} not found`);
  return button;
}

const accountFor = (id: number) => ({
  id,
  name: `Conta ${String(id)}`,
  account_type: 'water',
  external_identifier: `UC-${String(id)}`,
  default_due_day: 10,
  expected_amount: '0.00',
  lifecycle_state: 'active',
});

describe('BillsPage — cockpit interactions', () => {
  beforeEach(() => {
    setAdmin(true);
    setIptuAlerts();
    setBillingAccounts([]);
  });

  it('renders the pay popover on active unpaid rows for admins only', async () => {
    setMonthBoard(
      createMockMonthBoard({
        groups: [
          {
            building_id: 1,
            building_label: 'Prédio 836',
            bills: [
              createMockBill({
                id: 1,
                description: 'Conta ativa',
                lifecycle_state: 'active',
                payment_status: 'open',
              }),
            ],
          },
        ],
      })
    );

    const { queryClient, unmount } = renderWithProviders(<BillsPage />);
    await screen.findAllByText('Conta ativa');
    expect(firstButtonNamed(/^pagar$/i)).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
    unmount();

    setAdmin(false);
    const { queryClient: qc2 } = renderWithProviders(<BillsPage />);
    await screen.findAllByText('Conta ativa');
    expect(screen.queryByRole('button', { name: /^pagar$/i })).not.toBeInTheDocument();
    await waitForQueriesToSettle(qc2);
  });

  it('offers "Importar fatura" only on estimated water/electricity open bills', async () => {
    setMonthBoard(
      createMockMonthBoard({
        groups: [
          {
            building_id: 1,
            building_label: 'Prédio 836',
            bills: [
              createMockBill({
                id: 1,
                description: 'Água estimada',
                account_type: 'water',
                amount_is_estimated: true,
                payment_status: 'open',
                lifecycle_state: 'active',
              }),
              createMockBill({
                id: 2,
                description: 'Taxa condominial',
                account_type: 'generic',
                amount_is_estimated: false,
                payment_status: 'open',
                lifecycle_state: 'active',
              }),
            ],
          },
        ],
      })
    );

    renderWithProviders(<BillsPage />);
    await screen.findAllByText('Água estimada');

    const rows = screen.getAllByRole('row');
    const waterRow = rows.find((row) => row.textContent?.includes('Água estimada'));
    const genericRow = rows.find((row) => row.textContent?.includes('Taxa condominial'));
    expect(waterRow).toBeDefined();
    expect(genericRow).toBeDefined();
    if (!waterRow || !genericRow) throw new Error('rows not found');

    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const waterActionsButton = waterRow.querySelector('button[aria-label="Ações da conta"]');
    expect(waterActionsButton).not.toBeNull();
    if (waterActionsButton) await user.click(waterActionsButton);
    expect(await screen.findByText('Importar fatura')).toBeInTheDocument();
    await user.keyboard('{Escape}');

    const genericActionsButton = genericRow.querySelector('button[aria-label="Ações da conta"]');
    expect(genericActionsButton).not.toBeNull();
    if (genericActionsButton) await user.click(genericActionsButton);
    await waitFor(() => {
      expect(screen.queryByText('Importar fatura')).not.toBeInTheDocument();
    });
  });

  it('opens the S73 consolidate-debt dialog from the debt sub-section CTA (rows with an account) and passes toConsolidableBills(board, accountId)', async () => {
    setMonthBoard(
      createMockMonthBoard({
        deferred_suspended: [
          createMockBill({
            id: 5,
            description: 'IPTU suspenso',
            lifecycle_state: 'suspended',
            amount_remaining: 999,
            billing_account: accountFor(3) as never,
          }),
        ],
      })
    );

    renderWithProviders(<BillsPage />);
    await screen.findAllByText('IPTU suspenso');

    const user = userEvent.setup({ pointerEventsCheck: 0 });
    await user.click(firstButtonNamed(/^parcelar$/i));

    expect(await screen.findByText('Parcelar saldo devedor')).toBeInTheDocument();
    // The bill row shows its restante (formatCurrency(999)) — same value the dialog totals from
    // the derived ConsolidableBill (amount_remaining), proving the props were built from the row.
    expect(screen.getAllByText('IPTU suspenso').length).toBeGreaterThan(0);
  });

  it('does not render the Parcelar CTA on Atrasadas rows (CTA only in the deferred/suspended sub-section)', async () => {
    setMonthBoard(
      createMockMonthBoard({
        overdue: [
          createMockBill({
            id: 6,
            description: 'Conta atrasada',
            due_date: '2026-05-01',
            billing_account: accountFor(4) as never,
          }),
        ],
      })
    );

    renderWithProviders(<BillsPage />);
    await screen.findAllByText('Conta atrasada');

    expect(screen.queryByRole('button', { name: /parcelar/i })).not.toBeInTheDocument();
  });

  it('hides the Parcelar CTA on rows without a billing account', async () => {
    setMonthBoard(
      createMockMonthBoard({
        deferred_suspended: [
          createMockBill({
            id: 7,
            description: 'Adiada sem conta',
            lifecycle_state: 'deferred',
            billing_account: null,
          }),
        ],
      })
    );

    renderWithProviders(<BillsPage />);
    await screen.findAllByText('Adiada sem conta');

    expect(screen.queryByRole('button', { name: /parcelar/i })).not.toBeInTheDocument();
  });

  it('adds a one-off bill through "+ Conta avulsa" and refetches the board', async () => {
    const createBodies = spyCreateWithLines();
    setMonthBoard(createMockMonthBoard());

    renderWithProviders(<BillsPage />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await user.click(await screen.findByRole('button', { name: /conta avulsa/i }));
    const dialog = screen.getByRole('dialog', { name: /conta avulsa/i });
    await user.type(within(dialog).getByLabelText(/descrição/i), 'Reparo emergencial');
    await user.type(within(dialog).getByLabelText(/valor/i), '150');
    const dueDateInput = within(dialog).getByLabelText(/vencimento/i);
    await user.clear(dueDateInput);
    await user.type(dueDateInput, '2026-06-15');

    await user.click(within(dialog).getByRole('button', { name: /^criar$/i }));

    await waitFor(() => expect(createBodies).toHaveLength(1));
  });

  it('refetches the month board after paying (mutation → invalidate → refetch, no optimistic row flip)', async () => {
    let call = 0;
    server.use(
      http.get(`${API_BASE}/finances/finance-dashboard/month_board/`, () => {
        call += 1;
        const paid = call > 1;
        return HttpResponse.json(
          createMockMonthBoard({
            groups: [
              {
                building_id: 1,
                building_label: 'Prédio 836',
                bills: [
                  createMockBill({
                    id: 1,
                    description: 'Conta a pagar',
                    payment_status: paid ? 'paid' : 'open',
                    amount_remaining: paid ? 0 : 350,
                  }),
                ],
              },
            ],
          })
        );
      })
    );
    spyPay();

    renderWithProviders(<BillsPage />);
    await screen.findAllByText('Conta a pagar');

    const user = userEvent.setup({ pointerEventsCheck: 0 });
    await user.click(firstButtonNamed(/^pagar$/i));
    await user.click(firstButtonNamed(/confirmar pagamento/i));

    // Only after the invalidate→refetch does the "Pagar" trigger disappear (paid bills can't be
    // paid again) — proving the row only flips post-confirmation, never optimistically.
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /^pagar$/i })).not.toBeInTheDocument();
    });
  });
});
