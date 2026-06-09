import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { useAuthStore } from '@/store/auth-store';
import type { FinanceCategory } from '@/lib/schemas/finances/category.schema';
import FinanceCategoriesPage from '../page';

const deleteMutate = vi.fn();
const deleteMutateAsync = vi.fn().mockResolvedValue(undefined);
let categoriesData: FinanceCategory[] = [];

vi.mock('@/lib/api/hooks/use-finance-categories', () => ({
  useFinanceCategories: () => ({ data: categoriesData, isLoading: false, error: null }),
  useDeleteFinanceCategory: () => ({
    mutate: deleteMutate,
    mutateAsync: deleteMutateAsync,
    isPending: false,
  }),
}));

// The form modal fires its own read hooks; stub it to isolate the page.
vi.mock('../_components/finance-category-form-modal', () => ({
  FinanceCategoryFormModal: () => null,
}));

function setAdmin(isStaff: boolean) {
  useAuthStore.setState({
    user: { id: 1, email: 'u@e.com', first_name: 'U', last_name: 'T', is_staff: isStaff },
    isAuthenticated: true,
  });
}

beforeEach(() => {
  deleteMutate.mockClear();
  deleteMutateAsync.mockClear();
  categoriesData = [
    { id: 1, name: 'Impostos', color: '#6B7280', sort_order: 2, parent: null },
    { id: 2, name: 'Serviços/Utilidades', color: '#10B981', sort_order: 1, parent: null },
  ];
  useAuthStore.setState({ user: null, isAuthenticated: false });
});

describe('FinanceCategoriesPage', () => {
  it('renders the seeded categories', async () => {
    setAdmin(false);
    renderWithProviders(<FinanceCategoriesPage />);
    await waitFor(() => expect(screen.getByText('Categorias')).toBeInTheDocument());
    expect(screen.getAllByText('Impostos').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Serviços/Utilidades').length).toBeGreaterThan(0);
  });

  it('shows the create button only for admins', async () => {
    setAdmin(false);
    const { unmount } = renderWithProviders(<FinanceCategoriesPage />);
    await waitFor(() => expect(screen.getByText('Categorias')).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: /nova categoria/i })).not.toBeInTheDocument();
    unmount();

    setAdmin(true);
    renderWithProviders(<FinanceCategoriesPage />);
    await waitFor(() => expect(screen.getByText('Categorias')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /nova categoria/i })).toBeInTheDocument();
  });

  it('shows a PT empty state when there are no categories', async () => {
    setAdmin(true);
    categoriesData = [];
    renderWithProviders(<FinanceCategoriesPage />);
    await waitFor(() =>
      expect(screen.getByText('Nenhuma categoria cadastrada')).toBeInTheDocument(),
    );
  });
});
