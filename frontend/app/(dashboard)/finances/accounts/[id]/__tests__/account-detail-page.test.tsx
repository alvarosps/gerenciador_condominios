import { describe, it, expect, vi, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor, fireEvent, within } from '@testing-library/react';
import { useParams } from 'next/navigation';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockAccountStatement, createMockBillingAccount } from '@/tests/mocks/data/finances';
import { useAuthStore } from '@/store/auth-store';
import AccountDetailPage from '../page';

const API_BASE = 'http://localhost:8008/api';

vi.mock('next/navigation', () => ({
  useParams: vi.fn(() => ({ id: '1' })),
}));

function setAdmin() {
  useAuthStore.setState({
    user: { id: 1, email: 'admin@test.com', first_name: 'Ana', last_name: 'Admin', is_staff: true },
    isAuthenticated: true,
  });
}

function setNonAdmin() {
  useAuthStore.setState({
    user: { id: 2, email: 't@test.com', first_name: 'Tom', last_name: 'Tenant', is_staff: false },
    isAuthenticated: true,
  });
}

describe('AccountDetailPage', () => {
  beforeEach(() => {
    vi.mocked(useParams).mockReturnValue({ id: '1' });
    setAdmin();
  });

  it('renderiza os 3 StatCards com saldo devedor formatado, faturas em aberto e atraso médio "~N dias"', async () => {
    server.use(
      http.get(`${API_BASE}/finances/billing-accounts/1/statement/`, () =>
        HttpResponse.json(
          createMockAccountStatement({
            stats: { open_balance: '412.50', open_bills_count: 2, avg_delay_days: 6 },
          })
        )
      )
    );

    const { queryClient } = renderWithProviders(<AccountDetailPage />);

    expect(await screen.findByText('R$ 412,50')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('~6 dias')).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('mostra "—" no atraso médio quando avg_delay_days é null', async () => {
    server.use(
      http.get(`${API_BASE}/finances/billing-accounts/1/statement/`, () =>
        HttpResponse.json(
          createMockAccountStatement({
            stats: { open_balance: '0.00', open_bills_count: 0, avg_delay_days: null },
            months: [],
          })
        )
      )
    );

    const { queryClient } = renderWithProviders(<AccountDetailPage />);

    expect(await screen.findByText('—')).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('lista as linhas mês a mês com competência, vencimento, total/pago/resto e data de pagamento', async () => {
    server.use(
      http.get(`${API_BASE}/finances/billing-accounts/1/statement/`, () =>
        HttpResponse.json(
          createMockAccountStatement({
            months: [
              {
                bill_id: 10,
                competence_month: '2026-06-01',
                due_date: '2026-06-10',
                description: 'Conta de Luz',
                amount_total: '350.00',
                amount_paid: '350.00',
                amount_remaining: '0.00',
                payment_status: 'paid',
                lifecycle_state: 'active',
                amount_is_estimated: false,
                paid_date: '2026-06-09',
              },
            ],
          })
        )
      )
    );

    const { queryClient } = renderWithProviders(<AccountDetailPage />);

    // DataTable renders both the desktop table row and the mobile card for the same record
    // (toggled by CSS breakpoints, not conditional mounting) — assert with getAllByText.
    expect((await screen.findAllByText('Conta de Luz')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('10/06/2026').length).toBeGreaterThan(0);
    expect(screen.getAllByText('09/06/2026').length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('exibe badge "valor estimado" só na linha com amount_is_estimated=true', async () => {
    server.use(
      http.get(`${API_BASE}/finances/billing-accounts/1/statement/`, () =>
        HttpResponse.json(
          createMockAccountStatement({
            months: [
              {
                bill_id: 10,
                competence_month: '2026-06-01',
                due_date: '2026-06-10',
                description: 'Conta de Luz (estimada)',
                amount_total: '200.00',
                amount_paid: '0.00',
                amount_remaining: '200.00',
                payment_status: 'open',
                lifecycle_state: 'active',
                amount_is_estimated: true,
                paid_date: null,
              },
              {
                bill_id: 11,
                competence_month: '2026-07-01',
                due_date: '2026-07-10',
                description: 'Conta de Luz (real)',
                amount_total: '230.00',
                amount_paid: '0.00',
                amount_remaining: '230.00',
                payment_status: 'open',
                lifecycle_state: 'active',
                amount_is_estimated: false,
                paid_date: null,
              },
            ],
          })
        )
      )
    );

    const { queryClient } = renderWithProviders(<AccountDetailPage />);

    await screen.findAllByText('Conta de Luz (estimada)');
    // DataTable renders both the desktop table row and the mobile card for the same record, so
    // a single estimated bill produces 2 badges (one per view) — never 4 (both rows would if the
    // badge leaked onto the non-estimated bill too).
    expect(screen.getAllByText(/valor estimado/i)).toHaveLength(2);
    expect(screen.queryAllByText('Conta de Luz (real)').length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('renderiza planos vinculados com progresso "Parcela N/M" e badge Embutido/Avulso', async () => {
    server.use(
      http.get(`${API_BASE}/finances/billing-accounts/1/statement/`, () =>
        HttpResponse.json(
          createMockAccountStatement({
            plans: [
              {
                id: 5,
                description: 'Parcelamento água acumulada',
                installment_count: 6,
                materialized_count: 2,
                lifecycle_state: 'active',
                embedded: true,
              },
            ],
          })
        )
      )
    );

    const { queryClient } = renderWithProviders(<AccountDetailPage />);

    expect(await screen.findByText('Parcelamento água acumulada')).toBeInTheDocument();
    expect(screen.getByText('Parcela 2/6')).toBeInTheDocument();
    expect(screen.getByText('Embutido')).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('id inválido (ex.: "abc") mostra empty state PT com link Voltar, sem chamar a API', async () => {
    vi.mocked(useParams).mockReturnValue({ id: 'abc' });
    let calls = 0;
    server.use(
      http.get(`${API_BASE}/finances/billing-accounts/:id/statement/`, () => {
        calls += 1;
        return HttpResponse.json(createMockAccountStatement());
      })
    );

    renderWithProviders(<AccountDetailPage />);

    expect(await screen.findByText(/conta não encontrada/i)).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /voltar para contas cadastradas/i })
    ).toBeInTheDocument();
    expect(calls).toBe(0);
  });

  it('404 do backend mostra o mesmo empty state "Conta não encontrada"', async () => {
    server.use(
      http.get(
        `${API_BASE}/finances/billing-accounts/1/statement/`,
        () => new HttpResponse(null, { status: 404 })
      )
    );

    const { queryClient } = renderWithProviders(<AccountDetailPage />);

    expect(await screen.findByText(/conta não encontrada/i)).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /voltar para contas cadastradas/i })
    ).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('esconde "Parcelar saldo devedor" para non-admin', async () => {
    setNonAdmin();
    server.use(
      http.get(`${API_BASE}/finances/billing-accounts/1/statement/`, () =>
        HttpResponse.json(createMockAccountStatement())
      )
    );

    const { queryClient } = renderWithProviders(<AccountDetailPage />);

    await waitFor(() => {
      expect(screen.queryByText(/extrato da conta/i)).toBeInTheDocument();
    });
    expect(
      screen.queryByRole('button', { name: /parcelar saldo devedor/i })
    ).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('admin abre o dialog de consolidação apenas com as bills consolidáveis (resto>0, não-canceladas)', async () => {
    server.use(
      http.get(`${API_BASE}/finances/billing-accounts/1/statement/`, () =>
        HttpResponse.json(
          createMockAccountStatement({
            account: createMockBillingAccount({ id: 1 }),
            months: [
              {
                bill_id: 1,
                competence_month: '2026-05-01',
                due_date: '2026-05-10',
                description: 'Conta consolidável',
                amount_total: '200.00',
                amount_paid: '0.00',
                amount_remaining: '200.00',
                payment_status: 'open',
                lifecycle_state: 'active',
                amount_is_estimated: false,
                paid_date: null,
              },
              {
                bill_id: 2,
                competence_month: '2026-06-01',
                due_date: '2026-06-10',
                description: 'Conta quitada',
                amount_total: '100.00',
                amount_paid: '100.00',
                amount_remaining: '0.00',
                payment_status: 'paid',
                lifecycle_state: 'active',
                amount_is_estimated: false,
                paid_date: '2026-06-05',
              },
              {
                bill_id: 3,
                competence_month: '2026-04-01',
                due_date: '2026-04-10',
                description: 'Conta cancelada',
                amount_total: '80.00',
                amount_paid: '0.00',
                amount_remaining: '80.00',
                payment_status: 'open',
                lifecycle_state: 'canceled',
                amount_is_estimated: false,
                paid_date: null,
              },
            ],
          })
        )
      )
    );

    const { queryClient } = renderWithProviders(<AccountDetailPage />);

    const consolidateButton = await screen.findByRole('button', {
      name: /parcelar saldo devedor/i,
    });
    fireEvent.click(consolidateButton);

    // The dialog overlays the page — the underlying table stays mounted, so scope the
    // "consolidable only" assertion to elements found after the dialog opens (dialog role).
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getAllByText('Conta consolidável').length).toBeGreaterThan(0);
    expect(within(dialog).queryByText('Conta quitada')).not.toBeInTheDocument();
    expect(within(dialog).queryByText('Conta cancelada')).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });
});
