import { describe, it, expect, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import { createMockEmployee } from '@/tests/mocks/data/finances';
import EmployeesPage from '../page';

const API_BASE = 'http://localhost:8008/api';

// Real hooks (useEmployees / useDeleteEmployee) hit MSW (the HTTP boundary); the real auth store
// drives admin gating. Employee rows come from raw DRF payloads the hook parses with employeeSchema.
function setEmployees(employees: unknown[]) {
  server.use(http.get(`${API_BASE}/finances/employees/`, () => HttpResponse.json(employees)));
}

function setAdmin(isStaff: boolean) {
  useAuthStore.setState({
    user: { id: 1, email: 'u@e.com', first_name: 'U', last_name: 'T', is_staff: isStaff },
    isAuthenticated: true,
  });
}

/** Spy the soft-delete DELETE; records the deleted id parsed from the request path. */
function spyDelete() {
  const ids: number[] = [];
  server.use(
    http.delete(`${API_BASE}/finances/employees/:id/`, ({ params }) => {
      ids.push(Number(params.id));
      return new HttpResponse(null, { status: 204 });
    })
  );
  return ids;
}

/** Returns the first row-actions trigger (the responsive DataTable renders one per view). */
function getFirstMenu(): HTMLElement {
  const [menu] = screen.getAllByRole('button', { name: /ações do funcionário/i });
  if (!menu) throw new Error('No actions menu found');
  return menu;
}

beforeEach(() => {
  setEmployees([createMockEmployee()]);
  useAuthStore.setState({ user: null, isAuthenticated: false });
});

describe('EmployeesPage', () => {
  it('renders the payment type label, salary as currency and link', async () => {
    setAdmin(false);
    const { queryClient } = renderWithProviders(<EmployeesPage />);

    await waitFor(() => expect(screen.getByText('Folha de Pagamento')).toBeInTheDocument());
    await waitFor(() => expect(screen.getAllByText('Fixo').length).toBeGreaterThan(0));
    expect(screen.getAllByText('R$ 1.320,00').length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('shows "—" for a variable-only employee with no base salary (Raymel)', async () => {
    setAdmin(false);
    setEmployees([
      createMockEmployee({ name: 'Raymel', payment_type: 'variable', base_salary: null }),
    ]);
    const { queryClient } = renderWithProviders(<EmployeesPage />);

    await waitFor(() => expect(screen.getByText('Folha de Pagamento')).toBeInTheDocument());
    await waitFor(() => expect(screen.getAllByText('Variável').length).toBeGreaterThan(0));
    // The base-salary cell and the (empty) link cell both render the em dash.
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('renders the linked person name when present (Rosa-like)', async () => {
    setAdmin(false);
    setEmployees([
      createMockEmployee({
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
    ]);
    const { queryClient } = renderWithProviders(<EmployeesPage />);

    await waitFor(() => expect(screen.getByText('Folha de Pagamento')).toBeInTheDocument());
    await waitFor(() => expect(screen.getAllByText('Rosa Maria').length).toBeGreaterThan(0));

    await waitForQueriesToSettle(queryClient);
  });

  it('hides write actions for non-admins', async () => {
    setAdmin(false);
    const { queryClient } = renderWithProviders(<EmployeesPage />);

    await waitFor(() => expect(screen.getByText('Folha de Pagamento')).toBeInTheDocument());
    await waitFor(() => expect(screen.getAllByText('Fixo').length).toBeGreaterThan(0));
    expect(screen.queryByRole('button', { name: /novo funcionário/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /ações do funcionário/i })).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('shows write actions for admins', async () => {
    setAdmin(true);
    const { queryClient } = renderWithProviders(<EmployeesPage />);

    await waitFor(() => expect(screen.getByText('Folha de Pagamento')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /novo funcionário/i })).toBeInTheDocument();
    await waitFor(() =>
      expect(
        screen.getAllByRole('button', { name: /ações do funcionário/i }).length
      ).toBeGreaterThan(0)
    );

    await waitForQueriesToSettle(queryClient);
  });

  it('soft-deletes via the AlertDialog confirmation', async () => {
    const user = userEvent.setup();
    setAdmin(true);
    const deletedIds = spyDelete();
    const { queryClient } = renderWithProviders(<EmployeesPage />);
    await waitFor(() => expect(screen.getByText('Folha de Pagamento')).toBeInTheDocument());
    await waitFor(() =>
      expect(
        screen.getAllByRole('button', { name: /ações do funcionário/i }).length
      ).toBeGreaterThan(0)
    );

    await user.click(getFirstMenu());
    await user.click(await screen.findByText('Excluir'));

    const confirm = await screen.findByRole('button', { name: 'Excluir' });
    await user.click(confirm);

    await waitFor(() => expect(deletedIds).toContain(1));

    await waitForQueriesToSettle(queryClient);
  });

  it('shows a PT empty state when there are no employees', async () => {
    setAdmin(true);
    setEmployees([]);
    const { queryClient } = renderWithProviders(<EmployeesPage />);
    await waitFor(() =>
      expect(screen.getByText('Nenhum funcionário cadastrado')).toBeInTheDocument()
    );

    await waitForQueriesToSettle(queryClient);
  });
});
