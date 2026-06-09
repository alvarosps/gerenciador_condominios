import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/tests/test-utils';
import { useAuthStore } from '@/store/auth-store';
import type { InstallmentPlan } from '@/lib/schemas/finances/installment-plan.schema';
import InstallmentPlansPage from '../page';

const deleteMutate = vi.fn();
const deleteMutateAsync = vi.fn().mockResolvedValue(undefined);
let plansData: InstallmentPlan[] = [];

vi.mock('@/lib/api/hooks/use-installment-plans', () => ({
  useInstallmentPlans: () => ({ data: plansData, isLoading: false }),
  useDeleteInstallmentPlan: () => ({
    mutate: deleteMutate,
    mutateAsync: deleteMutateAsync,
    isPending: false,
  }),
}));

// The form modal and convert dialog fire their own read hooks; stub them to isolate the page.
vi.mock('../_components/installment-plan-form-modal', () => ({
  InstallmentPlanFormModal: () => null,
}));
vi.mock('../_components/convert-deferred-dialog', () => ({
  ConvertDeferredDialog: () => null,
}));

function makePlan(overrides: Partial<InstallmentPlan> = {}): InstallmentPlan {
  return {
    id: 1,
    description: 'IPTU 2026',
    total_amount: 1500,
    installment_count: 3,
    start_due_date: '2026-07-10',
    default_due_day: 10,
    lifecycle_state: 'active',
    embedded: false,
    category: null,
    category_id: null,
    building: null,
    building_id: null,
    billing_account: null,
    billing_account_id: null,
    installments: [],
    notes: '',
    ...overrides,
  };
}

function setAdmin(isStaff: boolean) {
  useAuthStore.setState({
    user: { id: 1, email: 'u@e.com', first_name: 'U', last_name: 'T', is_staff: isStaff },
    isAuthenticated: true,
  });
}

beforeEach(() => {
  deleteMutate.mockClear();
  deleteMutateAsync.mockClear();
  plansData = [makePlan()];
  useAuthStore.setState({ user: null, isAuthenticated: false });
});

/** Returns the first row-actions trigger (the responsive DataTable renders one per view). */
function getFirstMenu(): HTMLElement {
  const [menu] = screen.getAllByRole('button', { name: /ações do plano/i });
  if (!menu) throw new Error('No actions menu found');
  return menu;
}

describe('InstallmentPlansPage', () => {
  it('renders the total as currency and "Condomínio" when no building', async () => {
    setAdmin(false);
    renderWithProviders(<InstallmentPlansPage />);

    await waitFor(() => expect(screen.getByText('Planos de Parcelas')).toBeInTheDocument());
    expect(screen.getAllByText('R$ 1.500,00').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Condomínio').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Ativo').length).toBeGreaterThan(0);
  });

  it('hides write actions for non-admins (only the read-only schedule action remains)', async () => {
    const user = userEvent.setup();
    setAdmin(false);
    renderWithProviders(<InstallmentPlansPage />);

    await waitFor(() => expect(screen.getByText('Planos de Parcelas')).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: /novo plano/i })).not.toBeInTheDocument();

    // The actions menu still exists so read users can view the schedule, but no write items.
    await user.click(getFirstMenu());
    expect(await screen.findByText('Cronograma')).toBeInTheDocument();
    expect(screen.queryByText('Editar')).not.toBeInTheDocument();
    expect(screen.queryByText('Excluir')).not.toBeInTheDocument();
    expect(screen.queryByText('Converter adiado')).not.toBeInTheDocument();
  });

  it('shows write actions for admins', async () => {
    setAdmin(true);
    renderWithProviders(<InstallmentPlansPage />);

    await waitFor(() => expect(screen.getByText('Planos de Parcelas')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /novo plano/i })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /ações do plano/i }).length).toBeGreaterThan(0);
  });

  it('offers "Converter adiado" only for deferred plans', async () => {
    const user = userEvent.setup();
    setAdmin(true);
    plansData = [makePlan({ lifecycle_state: 'active' })];
    const { unmount } = renderWithProviders(<InstallmentPlansPage />);
    await waitFor(() => expect(screen.getByText('Planos de Parcelas')).toBeInTheDocument());

    await user.click(getFirstMenu());
    expect(screen.queryByText('Converter adiado')).not.toBeInTheDocument();
    unmount();

    plansData = [makePlan({ lifecycle_state: 'deferred' })];
    renderWithProviders(<InstallmentPlansPage />);
    await waitFor(() => expect(screen.getByText('Planos de Parcelas')).toBeInTheDocument());
    await user.click(getFirstMenu());
    expect(await screen.findByText('Converter adiado')).toBeInTheDocument();
  });

  it('soft-deletes via the AlertDialog confirmation', async () => {
    const user = userEvent.setup();
    setAdmin(true);
    renderWithProviders(<InstallmentPlansPage />);
    await waitFor(() => expect(screen.getByText('Planos de Parcelas')).toBeInTheDocument());

    await user.click(getFirstMenu());
    await user.click(await screen.findByText('Excluir'));

    const confirm = await screen.findByRole('button', { name: 'Excluir' });
    await user.click(confirm);

    await waitFor(() => expect(deleteMutateAsync).toHaveBeenCalledWith(1));
  });

  it('shows a PT empty state when there are no plans', async () => {
    setAdmin(true);
    plansData = [];
    renderWithProviders(<InstallmentPlansPage />);
    await waitFor(() =>
      expect(screen.getByText('Nenhum plano de parcelas cadastrado')).toBeInTheDocument(),
    );
  });
});
