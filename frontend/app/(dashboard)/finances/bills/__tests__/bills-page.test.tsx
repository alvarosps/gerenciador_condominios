import { describe, it, expect, beforeAll, beforeEach } from 'vitest';
import { http, HttpResponse, delay } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import { createMockBill } from '@/tests/mocks/data/finances';
import BillsPage from '../page';

// Real hooks (useBills / useGenerateMonthBills / …) hit MSW — no hook is mocked. The real auth
// store drives admin gating. generate_month is spied via an MSW request-body capture.
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

function setBillsResponse(bills: unknown[]) {
  server.use(http.get(`${API_BASE}/finances/bills/`, () => HttpResponse.json(bills)));
}

function setAdmin(isStaff: boolean) {
  useAuthStore.setState({
    user: { id: 1, email: 'a@b.c', first_name: 'A', last_name: 'B', is_staff: isStaff },
    isAuthenticated: true,
  });
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

// setBillsResponse ignores query params; this handler captures competence_month off each request.
function captureBillsParams() {
  const captured: { competence_month: string | null } = { competence_month: null };
  server.use(
    http.get(`${API_BASE}/finances/bills/`, ({ request }) => {
      captured.competence_month = new URL(request.url).searchParams.get('competence_month');
      return HttpResponse.json([]);
    })
  );
  return captured;
}

// Derive expected competence ISO from the same real clock the page reads (deterministic without
// fake timers; new Date(y, m, 1) normalises year rollover).
function monthIso(deltaMonths: number): string {
  const now = new Date();
  const d = new Date(now.getFullYear(), now.getMonth() + deltaMonths, 1);
  return `${String(d.getFullYear())}-${String(d.getMonth() + 1).padStart(2, '0')}-01`;
}

describe('BillsPage', () => {
  beforeEach(() => {
    setAdmin(false);
  });

  it('renders the table but hides all write buttons for non-admin users', async () => {
    setAdmin(false);
    setBillsResponse([createMockBill({ id: 1, description: 'Conta de Luz' })]);

    const { queryClient } = renderWithProviders(<BillsPage />);

    expect((await screen.findAllByText('Conta de Luz')).length).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: /nova conta/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /gerar contas do mês/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /ações da conta/i })).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('shows write buttons for admin and generate-month calls useGenerateMonthBills', async () => {
    setAdmin(true);
    const calls = spyGenerateMonth();
    setBillsResponse([createMockBill({ id: 1, description: 'Conta de Luz' })]);

    const { queryClient } = renderWithProviders(<BillsPage />);

    expect(await screen.findByRole('button', { name: /nova conta/i })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /gerar contas do mês/i }));

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
    // Use a month distinct from the current-month competence label so the assertion targets the
    // bill's column ("Março de 2026"), not the navigator label, and await the async bill load.
    setBillsResponse([
      createMockBill({ id: 1, competence_month: '2026-03-01', building: null, building_id: null }),
    ]);

    const { queryClient } = renderWithProviders(<BillsPage />);

    expect((await screen.findAllByText('Março de 2026')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('Condomínio')).length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('renders a lifecycle chip (not "Em atraso") for a deferred bill', async () => {
    setAdmin(false);
    setBillsResponse([
      createMockBill({
        id: 1,
        lifecycle_state: 'deferred',
        is_overdue: true,
        payment_status: 'open',
      }),
    ]);

    const { queryClient } = renderWithProviders(<BillsPage />);

    expect((await screen.findAllByText('Adiada')).length).toBeGreaterThan(0);
    expect(screen.queryByText('Em atraso')).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('shows the overdue chip for an overdue active bill', async () => {
    setAdmin(false);
    setBillsResponse([
      createMockBill({
        id: 1,
        lifecycle_state: 'active',
        is_overdue: true,
        payment_status: 'open',
      }),
    ]);

    const { queryClient } = renderWithProviders(<BillsPage />);

    expect((await screen.findAllByText('Em atraso')).length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('shows a loading skeleton then content', async () => {
    setAdmin(false);
    server.use(
      http.get(`${API_BASE}/finances/bills/`, async () => {
        await delay(50);
        return HttpResponse.json([createMockBill({ id: 1, description: 'Conta de Luz' })]);
      })
    );

    const { queryClient } = renderWithProviders(<BillsPage />);
    expect((await screen.findAllByText('Conta de Luz')).length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('shows a Portuguese empty state when there are no bills', async () => {
    setAdmin(false);
    setBillsResponse([]);

    const { queryClient } = renderWithProviders(<BillsPage />);

    expect(await screen.findByText('Nenhuma conta cadastrada')).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('por padrão busca a competência do mês corrente', async () => {
    setAdmin(true);
    const captured = captureBillsParams();

    const { queryClient } = renderWithProviders(<BillsPage />);

    await waitFor(() => expect(captured.competence_month).toBe(monthIso(0)));

    await waitForQueriesToSettle(queryClient);
  });

  it('chevron "Mês anterior" muda o competence_month para o mês anterior', async () => {
    setAdmin(true);
    const captured = captureBillsParams();

    const { queryClient } = renderWithProviders(<BillsPage />);
    await waitFor(() => expect(captured.competence_month).toBe(monthIso(0)));

    await userEvent.click(screen.getByRole('button', { name: 'Mês anterior' }));

    await waitFor(() => expect(captured.competence_month).toBe(monthIso(-1)));

    await waitForQueriesToSettle(queryClient);
  });

  it('chevron "Próximo mês" avança o competence_month', async () => {
    setAdmin(true);
    const captured = captureBillsParams();

    const { queryClient } = renderWithProviders(<BillsPage />);
    await waitFor(() => expect(captured.competence_month).toBe(monthIso(0)));

    await userEvent.click(screen.getByRole('button', { name: 'Próximo mês' }));

    await waitFor(() => expect(captured.competence_month).toBe(monthIso(1)));

    await waitForQueriesToSettle(queryClient);
  });

  it('alternar para "Todas as competências" remove o filtro de competência', async () => {
    setAdmin(true);
    // pointerEventsCheck:0 lets userEvent drive the Radix Select in happy-dom (same as the
    // other finance Select tests); findByRole waits for the listbox to open.
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const captured = captureBillsParams();

    const { queryClient } = renderWithProviders(<BillsPage />);
    await waitFor(() => expect(captured.competence_month).toBe(monthIso(0)));

    await user.click(screen.getByText('Mês selecionado'));
    await user.click(await screen.findByRole('option', { name: 'Todas as competências' }));

    await waitFor(() => expect(captured.competence_month).toBeNull());

    await waitForQueriesToSettle(queryClient);
  });

  it('chevrons ficam desabilitados em modo "Todas as competências"', async () => {
    setAdmin(true);
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    setBillsResponse([]);

    const { queryClient } = renderWithProviders(<BillsPage />);
    await screen.findByRole('button', { name: 'Mês anterior' });

    await user.click(screen.getByText('Mês selecionado'));
    await user.click(await screen.findByRole('option', { name: 'Todas as competências' }));

    expect(screen.getByRole('button', { name: 'Mês anterior' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Próximo mês' })).toBeDisabled();

    await waitForQueriesToSettle(queryClient);
  });

  it('"Gerar contas do mês" usa o mês selecionado', async () => {
    setAdmin(true);
    const calls = spyGenerateMonth();
    setBillsResponse([]);

    const { queryClient } = renderWithProviders(<BillsPage />);
    await userEvent.click(await screen.findByRole('button', { name: 'Mês anterior' }));
    await userEvent.click(screen.getByRole('button', { name: /gerar contas do mês/i }));

    await waitFor(() => expect(calls).toHaveLength(1));
    const prev = new Date(new Date().getFullYear(), new Date().getMonth() - 1, 1);
    expect(calls[0]).toMatchObject({ year: prev.getFullYear(), month: prev.getMonth() + 1 });

    await waitForQueriesToSettle(queryClient);
  });

  it('groups bills into one accordion per building (+ a Condomínio bucket) and shows the Tipo column', async () => {
    setAdmin(false);
    setBillsResponse([
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
      createMockBill({
        id: 2,
        description: 'IPTU dívida 2026',
        account_type: 'iptu',
        building: null,
        building_id: null,
      }),
    ]);

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
