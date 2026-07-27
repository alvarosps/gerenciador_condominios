import { describe, it, expect, beforeAll, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import { createMockBillingAccount } from '@/tests/mocks/data/finances';
import AccountsPage from '../page';

// Real hooks (useBillingAccounts / mutations / useBuildings) hit MSW — no hook is mocked. The
// real auth store drives admin gating (pattern from bills-page.test.tsx).
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

function setAccountsResponse(accounts: unknown[]) {
  server.use(http.get(`${API_BASE}/finances/billing-accounts/`, () => HttpResponse.json(accounts)));
}

function setAdmin(isStaff: boolean) {
  useAuthStore.setState({
    user: { id: 1, email: 'a@b.c', first_name: 'A', last_name: 'B', is_staff: isStaff },
    isAuthenticated: true,
  });
}

// setAccountsResponse ignores query params; this handler captures them off each request
// (pattern from captureBillsParams in bills-page.test.tsx).
function captureAccountsParams() {
  const captured: { building_id: string | null; account_type: string | null } = {
    building_id: null,
    account_type: null,
  };
  server.use(
    http.get(`${API_BASE}/finances/billing-accounts/`, ({ request }) => {
      const params = new URL(request.url).searchParams;
      captured.building_id = params.get('building_id');
      captured.account_type = params.get('account_type');
      return HttpResponse.json([]);
    })
  );
  return captured;
}

function setBuildingsEmpty() {
  server.use(http.get(`${API_BASE}/buildings/`, () => HttpResponse.json([])));
}

describe('AccountsPage', () => {
  beforeEach(() => {
    setAdmin(false);
    setBuildingsEmpty();
  });

  it('lista as contas com nome, tipo (label PT), prédio e saldo devedor formatado', async () => {
    setAccountsResponse([
      createMockBillingAccount({
        id: 1,
        name: 'Água DMAE 836',
        account_type: 'water',
        building: { id: 1, street_number: 836, name: 'Condomínio Steinmetz', address: 'Av. X' },
        open_balance: '412.50',
      }),
    ]);

    const { queryClient } = renderWithProviders(<AccountsPage />);

    // DataTable renders both a desktop table and a mobile card view of the same row —
    // every assertion here uses the AllBy* variant (pattern from bills-page.test.tsx).
    expect((await screen.findAllByText('Água DMAE 836')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Água').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Condomínio Steinmetz').length).toBeGreaterThan(0);
    expect(screen.getAllByText('R$ 412,50').length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('renderiza badge "Cortada" apenas para supply_status=cut', async () => {
    setAccountsResponse([
      createMockBillingAccount({ id: 1, name: 'Água Cortada', supply_status: 'cut' }),
      createMockBillingAccount({ id: 2, name: 'Luz Normal', supply_status: 'active' }),
    ]);

    const { queryClient } = renderWithProviders(<AccountsPage />);

    await screen.findAllByText('Água Cortada');
    // One "Cortada" badge per rendering surface (desktop table + mobile card) — never for the
    // active-supply row.
    expect(screen.getAllByText('Cortada').length).toBe(2);

    await waitForQueriesToSettle(queryClient);
  });

  it('exibe "—" no saldo devedor quando open_balance ausente (payload antigo)', async () => {
    const { open_balance: _open_balance, ...legacyAccount } = createMockBillingAccount({
      id: 1,
      name: 'Conta Legada',
    });
    setAccountsResponse([legacyAccount]);

    const { queryClient } = renderWithProviders(<AccountsPage />);

    await screen.findAllByText('Conta Legada');
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('a célula do nome é um link para /finances/accounts/{id}', async () => {
    setAccountsResponse([createMockBillingAccount({ id: 1, name: 'Água DMAE 836' })]);

    const { queryClient } = renderWithProviders(<AccountsPage />);

    const links = await screen.findAllByRole('link', { name: 'Água DMAE 836' });
    expect(links.length).toBeGreaterThan(0);
    links.forEach((link) => expect(link).toHaveAttribute('href', '/finances/accounts/1'));

    await waitForQueriesToSettle(queryClient);
  });

  it('filtra por tipo enviando account_type na query', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const captured = captureAccountsParams();

    const { queryClient } = renderWithProviders(<AccountsPage />);
    await waitFor(() => expect(captured.account_type).toBeNull());

    await user.click(screen.getByText('Todos os tipos'));
    await user.click(await screen.findByRole('option', { name: 'Água' }));

    await waitFor(() => expect(captured.account_type).toBe('water'));

    await waitForQueriesToSettle(queryClient);
  });

  it('filtra por prédio enviando building_id na query', async () => {
    server.use(
      http.get(`${API_BASE}/buildings/`, () =>
        HttpResponse.json([{ id: 7, street_number: 836, name: 'Steinmetz', address: 'Av. X' }])
      )
    );
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const captured = captureAccountsParams();

    const { queryClient } = renderWithProviders(<AccountsPage />);
    await waitFor(() => expect(captured.building_id).toBeNull());

    await user.click(screen.getByText('Todos os prédios'));
    await user.click(await screen.findByRole('option', { name: 'Steinmetz' }));

    await waitFor(() => expect(captured.building_id).toBe('7'));

    await waitForQueriesToSettle(queryClient);
  });

  it('esconde "Nova Conta Cadastrada" e a coluna Ações para non-admin', async () => {
    setAdmin(false);
    setAccountsResponse([createMockBillingAccount({ id: 1, name: 'Água DMAE 836' })]);

    const { queryClient } = renderWithProviders(<AccountsPage />);

    expect((await screen.findAllByText('Água DMAE 836')).length).toBeGreaterThan(0);
    expect(
      screen.queryByRole('button', { name: /nova conta cadastrada/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /ações da conta cadastrada/i })
    ).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('admin cria conta pelo modal e a lista invalida/refetcha', async () => {
    setAdmin(true);
    setAccountsResponse([]);
    server.use(
      http.get(`${API_BASE}/finances/finance-categories/`, () => HttpResponse.json([])),
      http.post(`${API_BASE}/finances/billing-accounts/`, async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(createMockBillingAccount({ id: 42, ...body }), { status: 201 });
      })
    );

    const { queryClient } = renderWithProviders(<AccountsPage />);

    await userEvent.click(await screen.findByRole('button', { name: /nova conta cadastrada/i }));
    await userEvent.type(screen.getByPlaceholderText('Ex: Água DMAE 836'), 'Conta Nova');
    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    await waitForQueriesToSettle(queryClient);
  });

  it('admin exclui conta via DeleteConfirmDialog', async () => {
    setAdmin(true);
    setAccountsResponse([createMockBillingAccount({ id: 1, name: 'Água DMAE 836' })]);
    let deleteCalled = false;
    server.use(
      http.delete(`${API_BASE}/finances/billing-accounts/1/`, () => {
        deleteCalled = true;
        return new HttpResponse(null, { status: 204 });
      })
    );

    const { queryClient } = renderWithProviders(<AccountsPage />);

    await screen.findAllByText('Água DMAE 836');
    // Desktop table + mobile card each render an "Ações" trigger — the first is the desktop one.
    const [actionButton] = screen.getAllByRole('button', { name: /ações da conta cadastrada/i });
    expect(actionButton).toBeDefined();
    if (!actionButton) throw new Error('action button not found');
    await userEvent.click(actionButton);
    await userEvent.click(await screen.findByRole('menuitem', { name: /excluir/i }));
    await userEvent.click(await screen.findByRole('button', { name: /^excluir$/i }));

    await waitFor(() => expect(deleteCalled).toBe(true));

    await waitForQueriesToSettle(queryClient);
  });

  it('mostra empty state PT quando a lista vem vazia', async () => {
    setAccountsResponse([]);

    const { queryClient } = renderWithProviders(<AccountsPage />);

    expect(await screen.findByText('Nenhuma conta cadastrada')).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });
});
