import { describe, it, expect, vi, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import { createMockInstallmentPlan } from '@/tests/mocks/data/finances';
import InstallmentPlansPage from '../page';

type InstallmentPlanRaw = ReturnType<typeof createMockInstallmentPlan>;

const API_BASE = 'http://localhost:8008/api';

// Real hooks (useInstallmentPlans / useDeleteInstallmentPlan) hit MSW; the real auth store drives
// the admin gating. The page mounts the form modal + convert dialog (closed), which fire their own
// read hooks (buildings / categories / billing-accounts) against the default handlers — every test
// ends with waitForQueriesToSettle so those background GETs are never aborted by teardown.
function setAdmin(isStaff: boolean) {
  useAuthStore.setState({
    user: { id: 1, email: 'u@e.com', first_name: 'U', last_name: 'T', is_staff: isStaff },
    isAuthenticated: true,
  });
}

function setPlans(plans: InstallmentPlanRaw[]) {
  server.use(http.get(`${API_BASE}/finances/installment-plans/`, () => HttpResponse.json(plans)));
}

function failPlans() {
  server.use(
    http.get(`${API_BASE}/finances/installment-plans/`, () =>
      HttpResponse.json({ error: 'boom' }, { status: 500 })
    )
  );
}

function spyDelete(planId: number) {
  const calls: number[] = [];
  server.use(
    http.delete(`${API_BASE}/finances/installment-plans/${planId}/`, () => {
      calls.push(planId);
      return new HttpResponse(null, { status: 204 });
    })
  );
  return calls;
}

/** Returns the first row-actions trigger (the responsive DataTable renders one per view). */
function getFirstMenu(): HTMLElement {
  const [menu] = screen.getAllByRole('button', { name: /ações do plano/i });
  if (!menu) throw new Error('No actions menu found');
  return menu;
}

beforeEach(() => {
  vi.mocked(toast.success).mockReset();
  vi.mocked(toast.error).mockReset();
  useAuthStore.setState({ user: null, isAuthenticated: false });
});

describe('InstallmentPlansPage', () => {
  it('renders the total as currency and "Condomínio" when no building', async () => {
    setAdmin(false);
    setPlans([createMockInstallmentPlan({ id: 1, total_amount: '1500.00', building: null })]);
    const { queryClient } = renderWithProviders(<InstallmentPlansPage />);

    await waitFor(() => expect(screen.getByText('Planos de Parcelas')).toBeInTheDocument());
    await waitFor(() => expect(screen.getAllByText('R$ 1.500,00').length).toBeGreaterThan(0));
    expect(screen.getAllByText('Condomínio').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Ativo').length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('hides write actions for non-admins (only the read-only schedule action remains)', async () => {
    const user = userEvent.setup();
    setAdmin(false);
    setPlans([createMockInstallmentPlan({ id: 1 })]);
    const { queryClient } = renderWithProviders(<InstallmentPlansPage />);

    await waitFor(() => expect(screen.getByText('Planos de Parcelas')).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: /novo plano/i })).not.toBeInTheDocument();

    // The actions menu still exists so read users can view the schedule, but no write items.
    await waitFor(() =>
      expect(screen.getAllByRole('button', { name: /ações do plano/i }).length).toBeGreaterThan(0)
    );
    await user.click(getFirstMenu());
    expect(await screen.findByText('Cronograma')).toBeInTheDocument();
    expect(screen.queryByText('Editar')).not.toBeInTheDocument();
    expect(screen.queryByText('Excluir')).not.toBeInTheDocument();
    expect(screen.queryByText('Converter adiado')).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('shows write actions for admins', async () => {
    setAdmin(true);
    setPlans([createMockInstallmentPlan({ id: 1 })]);
    const { queryClient } = renderWithProviders(<InstallmentPlansPage />);

    await waitFor(() => expect(screen.getByText('Planos de Parcelas')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /novo plano/i })).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getAllByRole('button', { name: /ações do plano/i }).length).toBeGreaterThan(0)
    );

    await waitForQueriesToSettle(queryClient);
  });

  it('offers "Converter adiado" only for deferred plans', async () => {
    const user = userEvent.setup();
    setAdmin(true);
    setPlans([createMockInstallmentPlan({ id: 1, lifecycle_state: 'active' })]);
    const { unmount, queryClient } = renderWithProviders(<InstallmentPlansPage />);
    await waitFor(() => expect(screen.getByText('Planos de Parcelas')).toBeInTheDocument());
    await waitFor(() =>
      expect(screen.getAllByRole('button', { name: /ações do plano/i }).length).toBeGreaterThan(0)
    );

    await user.click(getFirstMenu());
    expect(screen.queryByText('Converter adiado')).not.toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
    unmount();

    setPlans([createMockInstallmentPlan({ id: 1, lifecycle_state: 'deferred' })]);
    const second = renderWithProviders(<InstallmentPlansPage />);
    await waitFor(() => expect(screen.getByText('Planos de Parcelas')).toBeInTheDocument());
    await waitFor(() =>
      expect(screen.getAllByRole('button', { name: /ações do plano/i }).length).toBeGreaterThan(0)
    );
    await user.click(getFirstMenu());
    expect(await screen.findByText('Converter adiado')).toBeInTheDocument();

    await waitForQueriesToSettle(second.queryClient);
  });

  it('soft-deletes via the AlertDialog confirmation', async () => {
    const user = userEvent.setup();
    setAdmin(true);
    setPlans([createMockInstallmentPlan({ id: 1 })]);
    const deleteCalls = spyDelete(1);
    const { queryClient } = renderWithProviders(<InstallmentPlansPage />);
    await waitFor(() => expect(screen.getByText('Planos de Parcelas')).toBeInTheDocument());
    await waitFor(() =>
      expect(screen.getAllByRole('button', { name: /ações do plano/i }).length).toBeGreaterThan(0)
    );

    await user.click(getFirstMenu());
    await user.click(await screen.findByText('Excluir'));

    const confirm = await screen.findByRole('button', { name: 'Excluir' });
    await user.click(confirm);

    await waitFor(() => expect(deleteCalls).toEqual([1]));

    await waitForQueriesToSettle(queryClient);
  });

  it('shows a PT empty state when there are no plans', async () => {
    setAdmin(true);
    setPlans([]);
    const { queryClient } = renderWithProviders(<InstallmentPlansPage />);
    await waitFor(() =>
      expect(screen.getByText('Nenhum plano de parcelas cadastrado')).toBeInTheDocument()
    );

    await waitForQueriesToSettle(queryClient);
  });

  it('shows an error state (not the empty state) when the query fails', async () => {
    setAdmin(true);
    failPlans();
    const { queryClient } = renderWithProviders(<InstallmentPlansPage />);
    await waitFor(() =>
      expect(screen.getByText(/Erro ao carregar planos de parcelas/)).toBeInTheDocument()
    );
    // A failed request must NOT masquerade as "no data".
    expect(screen.queryByText('Nenhum plano de parcelas cadastrado')).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });
});
