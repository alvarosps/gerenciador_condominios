import { describe, it, expect, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import { createMockFinanceCategory } from '@/tests/mocks/data/finances';
import FinanceCategoriesPage from '../page';

const API_BASE = 'http://localhost:8008/api';

// Real useFinanceCategories / useDeleteFinanceCategory hit MSW (the HTTP boundary); the real auth
// store drives admin gating. The form modal mounts for real but stays closed (Radix renders no
// content), so no hook is mocked.
function setAdmin(isStaff: boolean) {
  useAuthStore.setState({
    user: { id: 1, email: 'u@e.com', first_name: 'U', last_name: 'T', is_staff: isStaff },
    isAuthenticated: true,
  });
}

function setCategories(categories: unknown[]) {
  server.use(
    http.get(`${API_BASE}/finances/finance-categories/`, () => HttpResponse.json(categories))
  );
}

const seeded = [
  createMockFinanceCategory({ id: 1, name: 'Impostos', color: '#6B7280', sort_order: 2 }),
  createMockFinanceCategory({
    id: 2,
    name: 'Serviços/Utilidades',
    color: '#10B981',
    sort_order: 1,
  }),
];

beforeEach(() => {
  useAuthStore.setState({ user: null, isAuthenticated: false });
  setCategories(seeded);
});

describe('FinanceCategoriesPage', () => {
  it('renders the seeded categories', async () => {
    setAdmin(false);
    const { queryClient } = renderWithProviders(<FinanceCategoriesPage />);
    await waitFor(() => expect(screen.getByText('Categorias')).toBeInTheDocument());
    await waitFor(() => expect(screen.getAllByText('Impostos').length).toBeGreaterThan(0));
    expect(screen.getAllByText('Serviços/Utilidades').length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('shows the create button only for admins', async () => {
    setAdmin(false);
    const { unmount, queryClient } = renderWithProviders(<FinanceCategoriesPage />);
    await waitFor(() => expect(screen.getByText('Categorias')).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: /nova categoria/i })).not.toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
    unmount();

    setAdmin(true);
    const { queryClient: adminClient } = renderWithProviders(<FinanceCategoriesPage />);
    await waitFor(() => expect(screen.getByText('Categorias')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /nova categoria/i })).toBeInTheDocument();

    await waitForQueriesToSettle(adminClient);
  });

  it('shows a PT empty state when there are no categories', async () => {
    setAdmin(true);
    setCategories([]);
    const { queryClient } = renderWithProviders(<FinanceCategoriesPage />);
    await waitFor(() =>
      expect(screen.getByText('Nenhuma categoria cadastrada')).toBeInTheDocument()
    );

    await waitForQueriesToSettle(queryClient);
  });
});
