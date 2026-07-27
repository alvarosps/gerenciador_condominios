import { describe, it, expect, beforeAll, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { toast } from 'sonner';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import { createMockBill, createMockMonthBoard } from '@/tests/mocks/data/finances';
import BillsPage from '../page';

// Real hooks (useMonthBoard / useGenerateMonthBills / …) hit MSW — no hook is mocked. The board is
// now the single source of data for this page: `useBills`/GET `/finances/bills/` must never be
// called from here (S74 contract — the source-of-truth check below asserts 0 calls).
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

// Registers a spy on GET /finances/bills/ so tests can assert it is never called (S74: useBills
// leaves the page). Returns the running call count.
function spyBillsListCalls(): { count: number } {
  const calls = { count: 0 };
  server.use(
    http.get(`${API_BASE}/finances/bills/`, () => {
      calls.count += 1;
      return HttpResponse.json([]);
    })
  );
  return calls;
}

function spyGenerateMonth(
  response: { created: number; bills: unknown[] } = { created: 2, bills: [] }
) {
  const calls: { year: number; month: number }[] = [];
  server.use(
    http.post(`${API_BASE}/finances/bills/generate_month/`, async ({ request }) => {
      const body = (await request.json()) as { year: number; month: number };
      calls.push(body);
      return HttpResponse.json(response);
    })
  );
  return calls;
}

describe('BillsPage — month board structure', () => {
  beforeEach(() => {
    setAdmin(true);
    setIptuAlerts();
    setBillingAccounts([]);
  });

  it('renders the page from month_board and never calls the bills list endpoint', async () => {
    const billsListCalls = spyBillsListCalls();
    setMonthBoard(createMockMonthBoard());

    const { queryClient } = renderWithProviders(<BillsPage />);

    await screen.findAllByText('Conta de Luz');
    await waitForQueriesToSettle(queryClient);

    expect(billsListCalls.count).toBe(0);
  });

  it('renders one accordion group per backend group, in backend order, with bill rows', async () => {
    setMonthBoard(
      createMockMonthBoard({
        groups: [
          {
            building_id: 1,
            building_label: 'Prédio 836',
            bills: [createMockBill({ id: 1, description: 'Água 836' })],
          },
          {
            building_id: 2,
            building_label: 'Prédio 850',
            bills: [createMockBill({ id: 2, description: 'Luz 850' })],
          },
          {
            building_id: null,
            building_label: 'Condomínio',
            bills: [createMockBill({ id: 3, description: 'Taxa condominial' })],
          },
        ],
      })
    );

    const { queryClient } = renderWithProviders(<BillsPage />);

    const headers = await screen.findAllByRole('button', { expanded: true });
    const headerLabels = headers.map((h) => h.textContent ?? '');
    const order = ['Prédio 836', 'Prédio 850', 'Condomínio'].map((label) =>
      headerLabels.findIndex((text) => text.includes(label))
    );
    expect(order).toEqual([...order].sort((a, b) => a - b));
    expect(order.every((index) => index !== -1)).toBe(true);

    expect(screen.getAllByText('Água 836').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Luz 850').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Taxa condominial').length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('renders the Atrasadas card above the accordion with cross-competence bills and a days-late badge', async () => {
    setMonthBoard(
      createMockMonthBoard({
        overdue: [
          createMockBill({
            id: 9,
            description: 'Conta muito atrasada',
            competence_month: '2026-05-01',
            due_date: '2026-05-10',
          }),
        ],
        groups: [
          {
            building_id: 1,
            building_label: 'Prédio 836',
            bills: [createMockBill({ id: 1, description: 'Conta do mês' })],
          },
        ],
        totals: { due: '0.00', paid: '0.00', remaining: '0.00', overdue: '350.00' },
      })
    );

    const { queryClient } = renderWithProviders(<BillsPage />);

    const overdueHeading = await screen.findByText('Atrasadas');
    expect(overdueHeading).toBeInTheDocument();
    expect(screen.getAllByText('Conta muito atrasada').length).toBeGreaterThan(0);

    // Atrasadas is above the accordion (per-building group) in document order.
    const groupHeader = await screen.findByText('Prédio 836');
    expect(
      overdueHeading.compareDocumentPosition(groupHeader) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();

    await waitForQueriesToSettle(queryClient);
  });

  it('renders the deferred/suspended sub-section with state badges and keeps it out of month totals', async () => {
    setMonthBoard(
      createMockMonthBoard({
        deferred_suspended: [
          createMockBill({
            id: 11,
            description: 'IPTU suspenso',
            lifecycle_state: 'suspended',
            amount_total: '9999.00',
            amount_remaining: '9999.00',
          }),
        ],
        // Every total is distinct from the others and from the deferred/suspended bill's own
        // amount (R$ 9.999,00), so a match here cannot be confused with any other rendered value.
        totals: { due: '111.00', paid: '22.00', remaining: '333.00', overdue: '44.00' },
      })
    );

    const { queryClient } = renderWithProviders(<BillsPage />);

    await screen.findByText('Dívida adiada/suspensa');
    expect(screen.getAllByText('IPTU suspenso').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Suspensa').length).toBeGreaterThan(0);
    // Totals shown are still the payload verbatim (not inflated by the deferred/suspended debt).
    expect(screen.getByText('R$ 333,00')).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('renders the month totals strip from the payload without recomputing', async () => {
    setMonthBoard(
      createMockMonthBoard({
        totals: { due: '100.00', paid: '40.00', remaining: '60.00', overdue: '25.00' },
      })
    );

    const { queryClient } = renderWithProviders(<BillsPage />);

    await screen.findByText('R$ 100,00');
    expect(screen.getByText('R$ 40,00')).toBeInTheDocument();
    expect(screen.getByText('R$ 60,00')).toBeInTheDocument();
    expect(screen.getByText('R$ 25,00')).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('shows the generate banner when missing_count > 0', async () => {
    setMonthBoard(createMockMonthBoard({ generation: { missing_count: 4 } }));

    const { queryClient } = renderWithProviders(<BillsPage />);

    expect(
      await screen.findByRole('button', { name: 'Gerar contas faltantes (4)' })
    ).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('hides the generate banner when missing_count is 0', async () => {
    setMonthBoard(createMockMonthBoard({ generation: { missing_count: 0 } }));

    const { queryClient } = renderWithProviders(<BillsPage />);
    await screen.findAllByText('Conta de Luz');

    expect(
      screen.queryByRole('button', { name: /Gerar contas faltantes/ })
    ).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('clicking "Gerar contas faltantes (N)" posts to generate_month and refetches the board', async () => {
    setMonthBoard(createMockMonthBoard({ generation: { missing_count: 2 } }));
    const calls = spyGenerateMonth({ created: 2, bills: [] });

    const { queryClient } = renderWithProviders(<BillsPage />);

    const button = await screen.findByRole('button', { name: 'Gerar contas faltantes (2)' });
    await userEvent.click(button);

    await waitFor(() => expect(calls).toHaveLength(1));

    await waitForQueriesToSettle(queryClient);
  });

  it('shows an actionable "Abrir fechamento" toast on a 400 closed-month error from generate_month', async () => {
    setMonthBoard(createMockMonthBoard({ generation: { missing_count: 1 } }));
    server.use(
      http.post(`${API_BASE}/finances/bills/generate_month/`, () =>
        HttpResponse.json({ detail: 'Competência 06/2026 está fechada.' }, { status: 400 })
      )
    );

    const { queryClient } = renderWithProviders(<BillsPage />);

    const button = await screen.findByRole('button', { name: 'Gerar contas faltantes (1)' });
    await userEvent.click(button);

    // sonner is globally mocked (tests/setup.ts) — assert the toast call (S76: actionable now),
    // not rendered DOM text.
    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        'Competência 06/2026 está fechada.',
        expect.objectContaining({
          action: expect.objectContaining({ label: 'Abrir fechamento' }) as unknown,
        })
      )
    );

    await waitForQueriesToSettle(queryClient);
  });

  it('keeps the situação filter working client-side and drops the "Canceladas" option', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    setMonthBoard(
      createMockMonthBoard({
        deferred_suspended: [
          createMockBill({ id: 21, description: 'Conta suspensa', lifecycle_state: 'suspended' }),
        ],
        groups: [
          {
            building_id: 1,
            building_label: 'Prédio 836',
            bills: [createMockBill({ id: 1, description: 'Água 836', lifecycle_state: 'active' })],
          },
        ],
      })
    );

    const { queryClient } = renderWithProviders(<BillsPage />);
    await screen.findAllByText('Água 836');

    await user.click(screen.getByText('Todas as situações'));
    expect(screen.queryByRole('option', { name: 'Canceladas' })).not.toBeInTheDocument();
    await user.click(await screen.findByRole('option', { name: 'Suspensas' }));

    await waitFor(() => expect(screen.queryByText('Água 836')).not.toBeInTheDocument());
    expect(screen.getAllByText('Conta suspensa').length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('removes the competence-mode select ("Todas as competências")', async () => {
    setMonthBoard(createMockMonthBoard());

    const { queryClient } = renderWithProviders(<BillsPage />);
    await screen.findAllByText('Conta de Luz');

    expect(screen.queryByText('Mês selecionado')).not.toBeInTheDocument();
    expect(screen.queryByText('Todas as competências')).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('hides the generate banner and admin actions for non-admin users', async () => {
    setAdmin(false);
    setMonthBoard(createMockMonthBoard({ generation: { missing_count: 5 } }));

    const { queryClient } = renderWithProviders(<BillsPage />);
    await screen.findAllByText('Conta de Luz');

    expect(
      screen.queryByRole('button', { name: /Gerar contas faltantes/ })
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /nova conta/i })).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('shows the empty state when the board has no bills at all', async () => {
    setMonthBoard(createMockMonthBoard({ overdue: [], deferred_suspended: [], groups: [] }));

    const { queryClient } = renderWithProviders(<BillsPage />);

    expect(await screen.findByText('Nenhuma conta cadastrada')).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });
});

describe('BillsPage — "Gerar contas do mês" header action (always-available path)', () => {
  beforeEach(() => {
    setIptuAlerts();
    setBillingAccounts([]);
  });

  it('shows the header action for admin users', async () => {
    setAdmin(true);
    setMonthBoard(createMockMonthBoard({ generation: { missing_count: 0 } }));

    const { queryClient } = renderWithProviders(<BillsPage />);

    expect(await screen.findByRole('button', { name: 'Gerar contas do mês' })).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('hides the header action for non-admin users', async () => {
    setAdmin(false);
    setMonthBoard(createMockMonthBoard({ generation: { missing_count: 0 } }));

    const { queryClient } = renderWithProviders(<BillsPage />);
    await screen.findAllByText('Conta de Luz');

    expect(screen.queryByRole('button', { name: 'Gerar contas do mês' })).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('is available even when missing_count is 0 (unlike the contextual banner)', async () => {
    setAdmin(true);
    setMonthBoard(createMockMonthBoard({ generation: { missing_count: 0 } }));

    const { queryClient } = renderWithProviders(<BillsPage />);

    expect(await screen.findByRole('button', { name: 'Gerar contas do mês' })).toBeInTheDocument();
    // The contextual banner stays hidden — the header action is the always-available path.
    expect(
      screen.queryByRole('button', { name: /Gerar contas faltantes/ })
    ).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it("clicking it posts generate_month with the selected month's {year, month}", async () => {
    setAdmin(true);
    setMonthBoard(createMockMonthBoard({ generation: { missing_count: 0 } }));
    const calls = spyGenerateMonth({ created: 3, bills: [] });

    const { queryClient } = renderWithProviders(<BillsPage />);
    const button = await screen.findByRole('button', { name: 'Gerar contas do mês' });
    await userEvent.click(await screen.findByRole('button', { name: 'Mês anterior' }));
    await userEvent.click(button);

    await waitFor(() => expect(calls).toHaveLength(1));
    const prev = new Date(new Date().getFullYear(), new Date().getMonth() - 1, 1);
    expect(calls[0]).toMatchObject({ year: prev.getFullYear(), month: prev.getMonth() + 1 });

    await waitForQueriesToSettle(queryClient);
  });

  it('shows an actionable "Abrir fechamento" toast on a 400 closed-month error from the header action', async () => {
    setAdmin(true);
    setMonthBoard(createMockMonthBoard({ generation: { missing_count: 0 } }));
    server.use(
      http.post(`${API_BASE}/finances/bills/generate_month/`, () =>
        HttpResponse.json({ detail: 'Competência 06/2026 está fechada.' }, { status: 400 })
      )
    );

    const { queryClient } = renderWithProviders(<BillsPage />);
    const button = await screen.findByRole('button', { name: 'Gerar contas do mês' });
    await userEvent.click(button);

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        'Competência 06/2026 está fechada.',
        expect.objectContaining({
          action: expect.objectContaining({ label: 'Abrir fechamento' }) as unknown,
        })
      )
    );

    await waitForQueriesToSettle(queryClient);
  });
});

describe('BillsPage — estimate badges via month board (Descrição column)', () => {
  beforeEach(() => {
    setAdmin(true);
    setIptuAlerts();
    setBillingAccounts([]);
  });

  it('shows "valor estimado" badge for an estimated bill with a non-zero total', async () => {
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
                amount_is_estimated: true,
                amount_total: '120.00',
              }),
            ],
          },
        ],
      })
    );

    const { queryClient } = renderWithProviders(<BillsPage />);

    // DataTable renders both the desktop table and a CSS-hidden mobile card view; scope to the
    // table cell (`td`) so the assertion targets a single, unambiguous element.
    const matches = await screen.findAllByText('Água estimada');
    const cell = matches
      .map((el) => el.closest('td'))
      .find((el): el is HTMLTableCellElement => el !== null);
    expect(cell).toBeDefined();
    if (!cell) throw new Error('table cell not found');
    expect(within(cell).getByText('valor estimado')).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('shows "aguardando fatura" badge for an estimated bill with a zero total', async () => {
    setMonthBoard(
      createMockMonthBoard({
        groups: [
          {
            building_id: 1,
            building_label: 'Prédio 836',
            bills: [
              createMockBill({
                id: 1,
                description: 'Água sem fatura',
                amount_is_estimated: true,
                amount_total: '0.00',
                amount_remaining: '0.00',
              }),
            ],
          },
        ],
      })
    );

    const { queryClient } = renderWithProviders(<BillsPage />);

    const matches = await screen.findAllByText('Água sem fatura');
    const cell = matches
      .map((el) => el.closest('td'))
      .find((el): el is HTMLTableCellElement => el !== null);
    expect(cell).toBeDefined();
    if (!cell) throw new Error('table cell not found');
    expect(within(cell).getByText('aguardando fatura')).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });
});
