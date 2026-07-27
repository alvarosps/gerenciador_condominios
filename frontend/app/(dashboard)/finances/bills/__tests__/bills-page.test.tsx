import { describe, it, expect, beforeAll, beforeEach } from 'vitest';
import { http, HttpResponse, delay } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import { createMockBill, createMockMonthBoard } from '@/tests/mocks/data/finances';
import BillsPage from '../page';

// Real hooks (useMonthBoard / useGenerateMonthBills / …) hit MSW — no hook is mocked. The real auth
// store drives admin gating. generate_month is spied via an MSW request-body capture. The page's
// single data source is month_board (S74) — competence navigation is exercised via the params
// captured on that endpoint, not on the legacy bills list.
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

// Spy generate_month via an MSW request-body capture (the real useGenerateMonthBills hook POSTs
// here). Returns the captured {year, month} payloads.
function spyGenerateMonth() {
  const calls: { year: number; month: number }[] = [];
  server.use(
    http.post(`${API_BASE}/finances/bills/generate_month/`, async ({ request }) => {
      const body = (await request.json()) as { year: number; month: number };
      calls.push({ year: body.year, month: body.month });
      return HttpResponse.json({
        created: 1,
        bills: [createMockBill({ competence_month: '2026-06-01' })],
      });
    })
  );
  return calls;
}

// month_board ignores its query params by default; this handler captures year/month off each
// request so the navigator/generate-month assertions can check what the page actually sent.
function captureMonthBoardParams() {
  const captured: { year: string | null; month: string | null } = { year: null, month: null };
  server.use(
    http.get(`${API_BASE}/finances/finance-dashboard/month_board/`, ({ request }) => {
      const params = new URL(request.url).searchParams;
      captured.year = params.get('year');
      captured.month = params.get('month');
      return HttpResponse.json(createMockMonthBoard({ groups: [] }));
    })
  );
  return captured;
}

function currentPeriod(deltaMonths: number): { year: number; month: number } {
  const now = new Date();
  const d = new Date(now.getFullYear(), now.getMonth() + deltaMonths, 1);
  return { year: d.getFullYear(), month: d.getMonth() + 1 };
}

describe('BillsPage', () => {
  beforeEach(() => {
    setAdmin(false);
    setIptuAlerts();
    setBillingAccounts([]);
  });

  it('renders the table but hides all write buttons for non-admin users', async () => {
    setAdmin(false);
    setMonthBoard(
      createMockMonthBoard({
        groups: [
          {
            building_id: 1,
            building_label: 'Prédio 836',
            bills: [createMockBill({ id: 1, description: 'Conta de Luz' })],
          },
        ],
      })
    );

    const { queryClient } = renderWithProviders(<BillsPage />);

    expect((await screen.findAllByText('Conta de Luz')).length).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: /nova conta/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Gerar contas do mês' })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /gerar contas faltantes/i })
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /ações da conta/i })).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('shows write buttons (incl. the always-available header action) for admin, and the generate-missing banner calls useGenerateMonthBills', async () => {
    setAdmin(true);
    const calls = spyGenerateMonth();
    setMonthBoard(
      createMockMonthBoard({
        groups: [
          {
            building_id: 1,
            building_label: 'Prédio 836',
            bills: [createMockBill({ id: 1, description: 'Conta de Luz' })],
          },
        ],
        generation: { missing_count: 1 },
      })
    );

    const { queryClient } = renderWithProviders(<BillsPage />);

    expect(await screen.findByRole('button', { name: /nova conta/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Gerar contas do mês' })).toBeInTheDocument();
    await userEvent.click(
      await screen.findByRole('button', { name: 'Gerar contas faltantes (1)' })
    );

    await waitFor(() => {
      expect(calls).toHaveLength(1);
    });
    expect(calls[0]).toMatchObject({
      year: expect.any(Number) as number,
      month: expect.any(Number) as number,
    });

    await waitForQueriesToSettle(queryClient);
  });

  it('formats competence via split + formatMonthYear and shows "Condomínio" for null building', async () => {
    setAdmin(false);
    setMonthBoard(
      createMockMonthBoard({
        groups: [
          {
            building_id: null,
            building_label: 'Condomínio',
            bills: [
              createMockBill({
                id: 1,
                competence_month: '2026-03-01',
                building: null,
                building_id: null,
              }),
            ],
          },
        ],
      })
    );

    const { queryClient } = renderWithProviders(<BillsPage />);

    expect((await screen.findAllByText('Março de 2026')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('Condomínio')).length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('renders a lifecycle chip (not "Em atraso") for a deferred bill', async () => {
    setAdmin(false);
    setMonthBoard(
      createMockMonthBoard({
        groups: [
          {
            building_id: 1,
            building_label: 'Prédio 836',
            bills: [
              createMockBill({
                id: 1,
                lifecycle_state: 'deferred',
                is_overdue: true,
                payment_status: 'open',
              }),
            ],
          },
        ],
      })
    );

    const { queryClient } = renderWithProviders(<BillsPage />);

    expect((await screen.findAllByText('Adiada')).length).toBeGreaterThan(0);
    expect(screen.queryByText('Em atraso')).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('shows the overdue chip for an overdue active bill', async () => {
    setAdmin(false);
    setMonthBoard(
      createMockMonthBoard({
        groups: [
          {
            building_id: 1,
            building_label: 'Prédio 836',
            bills: [
              createMockBill({
                id: 1,
                lifecycle_state: 'active',
                is_overdue: true,
                payment_status: 'open',
              }),
            ],
          },
        ],
      })
    );

    const { queryClient } = renderWithProviders(<BillsPage />);

    expect((await screen.findAllByText('Em atraso')).length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('shows a loading skeleton then content', async () => {
    setAdmin(false);
    server.use(
      http.get(`${API_BASE}/finances/finance-dashboard/month_board/`, async () => {
        await delay(50);
        return HttpResponse.json(
          createMockMonthBoard({
            groups: [
              {
                building_id: 1,
                building_label: 'Prédio 836',
                bills: [createMockBill({ id: 1, description: 'Conta de Luz' })],
              },
            ],
          })
        );
      })
    );

    const { queryClient } = renderWithProviders(<BillsPage />);
    expect((await screen.findAllByText('Conta de Luz')).length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('shows a Portuguese empty state when there are no bills', async () => {
    setAdmin(false);
    setMonthBoard(createMockMonthBoard({ overdue: [], deferred_suspended: [], groups: [] }));

    const { queryClient } = renderWithProviders(<BillsPage />);

    expect(await screen.findByText('Nenhuma conta cadastrada')).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('por padrão busca a competência do mês corrente', async () => {
    setAdmin(true);
    const captured = captureMonthBoardParams();

    const { queryClient } = renderWithProviders(<BillsPage />);

    const expected = currentPeriod(0);
    await waitFor(() => expect(captured.year).toBe(String(expected.year)));
    expect(captured.month).toBe(String(expected.month));

    await waitForQueriesToSettle(queryClient);
  });

  it('chevron "Mês anterior" muda o mês do board para o mês anterior', async () => {
    setAdmin(true);
    const captured = captureMonthBoardParams();

    const { queryClient } = renderWithProviders(<BillsPage />);
    const initial = currentPeriod(0);
    await waitFor(() => expect(captured.month).toBe(String(initial.month)));

    await userEvent.click(screen.getByRole('button', { name: 'Mês anterior' }));

    const previous = currentPeriod(-1);
    await waitFor(() => expect(captured.month).toBe(String(previous.month)));
    expect(captured.year).toBe(String(previous.year));

    await waitForQueriesToSettle(queryClient);
  });

  it('chevron "Próximo mês" avança o mês do board', async () => {
    setAdmin(true);
    const captured = captureMonthBoardParams();

    const { queryClient } = renderWithProviders(<BillsPage />);
    const initial = currentPeriod(0);
    await waitFor(() => expect(captured.month).toBe(String(initial.month)));

    await userEvent.click(screen.getByRole('button', { name: 'Próximo mês' }));

    const next = currentPeriod(1);
    await waitFor(() => expect(captured.month).toBe(String(next.month)));
    expect(captured.year).toBe(String(next.year));

    await waitForQueriesToSettle(queryClient);
  });

  it('"Gerar contas faltantes" usa o mês selecionado', async () => {
    setAdmin(true);
    const calls = spyGenerateMonth();
    setMonthBoard(createMockMonthBoard({ groups: [], generation: { missing_count: 1 } }));

    const { queryClient } = renderWithProviders(<BillsPage />);
    await userEvent.click(await screen.findByRole('button', { name: 'Mês anterior' }));
    await userEvent.click(
      await screen.findByRole('button', { name: 'Gerar contas faltantes (1)' })
    );

    await waitFor(() => expect(calls).toHaveLength(1));
    const prev = currentPeriod(-1);
    expect(calls[0]).toMatchObject({ year: prev.year, month: prev.month });

    await waitForQueriesToSettle(queryClient);
  });

  it('groups bills into one accordion per building (+ a Condomínio bucket) and shows the Tipo column', async () => {
    setAdmin(false);
    setMonthBoard(
      createMockMonthBoard({
        groups: [
          {
            building_id: 1,
            building_label: 'Condomínio Steinmetz — Nº 836',
            bills: [
              createMockBill({
                id: 1,
                description: 'Água DMAE 836',
                account_type: 'water',
                building: {
                  id: 1,
                  street_number: 836,
                  name: 'Condomínio Steinmetz',
                  address: 'Av. Circular 836',
                },
                building_id: 1,
              }),
            ],
          },
          {
            building_id: null,
            building_label: 'Condomínio',
            bills: [
              createMockBill({
                id: 2,
                description: 'IPTU dívida 2026',
                account_type: 'iptu',
                building: null,
                building_id: null,
              }),
            ],
          },
        ],
      })
    );

    const { queryClient } = renderWithProviders(<BillsPage />);

    // One group header per building + the Condomínio bucket for the null-building bill.
    expect(await screen.findByText('Condomínio Steinmetz — Nº 836')).toBeInTheDocument();
    expect(screen.getAllByText('Condomínio').length).toBeGreaterThan(0);
    // The derived "Tipo" column renders the PT account-type labels.
    expect(screen.getAllByText('Água').length).toBeGreaterThan(0);
    expect(screen.getAllByText('IPTU').length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });
});
