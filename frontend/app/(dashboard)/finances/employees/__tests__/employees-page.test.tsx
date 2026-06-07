import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/tests/test-utils';
import { useAuthStore } from '@/store/auth-store';
import type { Employee } from '@/lib/schemas/finances/employee.schema';
import EmployeesPage from '../page';

const deleteMutateAsync = vi.fn().mockResolvedValue(undefined);
let employeesData: Employee[] = [];

vi.mock('@/lib/api/hooks/use-employees', () => ({
  useEmployees: () => ({ data: employeesData, isLoading: false }),
  useDeleteEmployee: () => ({
    mutate: vi.fn(),
    mutateAsync: deleteMutateAsync,
    isPending: false,
  }),
}));

vi.mock('../_components/employee-form-modal', () => ({
  EmployeeFormModal: () => null,
}));

function makeEmployee(overrides: Partial<Employee> = {}): Employee {
  return {
    id: 1,
    name: 'Adriana',
    role: 'Faxineira',
    payment_type: 'fixed',
    base_salary: 1320,
    default_due_day: 5,
    is_active: true,
    notes: '',
    person: null,
    person_id: null,
    lease: null,
    lease_id: null,
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
  deleteMutateAsync.mockClear();
  employeesData = [makeEmployee()];
  useAuthStore.setState({ user: null, isAuthenticated: false });
});

/** Returns the first row-actions trigger (the responsive DataTable renders one per view). */
function getFirstMenu(): HTMLElement {
  const [menu] = screen.getAllByRole('button', { name: /ações do funcionário/i });
  if (!menu) throw new Error('No actions menu found');
  return menu;
}

describe('EmployeesPage', () => {
  it('renders the payment type label, salary as currency and link', async () => {
    setAdmin(false);
    renderWithProviders(<EmployeesPage />);

    await waitFor(() => expect(screen.getByText('Folha de Pagamento')).toBeInTheDocument());
    expect(screen.getAllByText('Fixo').length).toBeGreaterThan(0);
    expect(screen.getAllByText('R$ 1.320,00').length).toBeGreaterThan(0);
  });

  it('shows "—" for a variable-only employee with no base salary (Raymel)', async () => {
    setAdmin(false);
    employeesData = [makeEmployee({ name: 'Raymel', payment_type: 'variable', base_salary: null })];
    renderWithProviders(<EmployeesPage />);

    await waitFor(() => expect(screen.getByText('Folha de Pagamento')).toBeInTheDocument());
    expect(screen.getAllByText('Variável').length).toBeGreaterThan(0);
    // The base-salary cell and the (empty) link cell both render the em dash.
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  });

  it('renders the linked person name when present (Rosa-like)', async () => {
    setAdmin(false);
    employeesData = [
      makeEmployee({
        name: 'Rosa',
        payment_type: 'mixed',
        person: {
          id: 2,
          name: 'Rosa Maria',
          relationship: 'Funcionária',
          phone: '',
          email: '',
          is_owner: false,
          is_employee: true,
          notes: '',
        },
      }),
    ];
    renderWithProviders(<EmployeesPage />);

    await waitFor(() => expect(screen.getByText('Folha de Pagamento')).toBeInTheDocument());
    expect(screen.getAllByText('Rosa Maria').length).toBeGreaterThan(0);
  });

  it('hides write actions for non-admins', async () => {
    setAdmin(false);
    renderWithProviders(<EmployeesPage />);

    await waitFor(() => expect(screen.getByText('Folha de Pagamento')).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: /novo funcionário/i })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /ações do funcionário/i }),
    ).not.toBeInTheDocument();
  });

  it('shows write actions for admins', async () => {
    setAdmin(true);
    renderWithProviders(<EmployeesPage />);

    await waitFor(() => expect(screen.getByText('Folha de Pagamento')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /novo funcionário/i })).toBeInTheDocument();
    expect(
      screen.getAllByRole('button', { name: /ações do funcionário/i }).length,
    ).toBeGreaterThan(0);
  });

  it('soft-deletes via the AlertDialog confirmation', async () => {
    const user = userEvent.setup();
    setAdmin(true);
    renderWithProviders(<EmployeesPage />);
    await waitFor(() => expect(screen.getByText('Folha de Pagamento')).toBeInTheDocument());

    await user.click(getFirstMenu());
    await user.click(await screen.findByText('Excluir'));

    const confirm = await screen.findByRole('button', { name: 'Excluir' });
    await user.click(confirm);

    await waitFor(() => expect(deleteMutateAsync).toHaveBeenCalledWith(1));
  });

  it('shows a PT empty state when there are no employees', async () => {
    setAdmin(true);
    employeesData = [];
    renderWithProviders(<EmployeesPage />);
    await waitFor(() =>
      expect(screen.getByText('Nenhum funcionário cadastrado')).toBeInTheDocument(),
    );
  });
});
