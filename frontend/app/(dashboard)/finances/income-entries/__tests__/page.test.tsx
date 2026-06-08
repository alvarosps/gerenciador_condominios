import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import { renderWithProviders, createTestQueryClient } from '@/tests/test-utils';
import IncomeEntriesPage from '../page';
import { createMockIncomeEntry } from '@/tests/mocks/data/finances';
import type * as incomeHooks from '@/lib/api/hooks/use-income-entries';
import type * as buildingHooks from '@/lib/api/hooks/use-buildings';
import type * as categoryHooks from '@/lib/api/hooks/use-finance-categories';
import type * as authStore from '@/store/auth-store';

type IncomeEntriesResult = ReturnType<typeof incomeHooks.useIncomeEntries>;
type DeleteResult = ReturnType<typeof incomeHooks.useDeleteIncomeEntry>;
type BuildingsResult = ReturnType<typeof buildingHooks.useBuildings>;
type CategoriesResult = ReturnType<typeof categoryHooks.useFinanceCategories>;
type AuthStoreResult = ReturnType<typeof authStore.useAuthStore>;

// Use vi.hoisted so mock variables are available when vi.mock factories run
const {
  mockUseIncomeEntries,
  mockUseDeleteIncomeEntry,
  mockUseBuildings,
  mockUseFinanceCategories,
  mockUseAuthStore,
} = vi.hoisted(() => ({
  mockUseIncomeEntries: vi.fn<typeof incomeHooks.useIncomeEntries>(),
  mockUseDeleteIncomeEntry: vi.fn<() => DeleteResult>(),
  mockUseBuildings: vi.fn<() => BuildingsResult>(),
  mockUseFinanceCategories: vi.fn<() => CategoriesResult>(),
  mockUseAuthStore: vi.fn<() => AuthStoreResult>(),
}));

// Mock the form modal to avoid dynamic import complications in vitest
vi.mock('@/app/(dashboard)/finances/income-entries/_components/income-entry-form-modal', () => ({
  IncomeEntryFormModal: () => null,
}));

vi.mock('@/lib/api/hooks/use-income-entries', () => ({
  useIncomeEntries: mockUseIncomeEntries,
  useDeleteIncomeEntry: mockUseDeleteIncomeEntry,
  useCreateIncomeEntry: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateIncomeEntry: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock('@/lib/api/hooks/use-buildings', () => ({
  useBuildings: mockUseBuildings,
}));
vi.mock('@/lib/api/hooks/use-finance-categories', () => ({
  useFinanceCategories: mockUseFinanceCategories,
}));
vi.mock('@/store/auth-store', () => ({
  useAuthStore: mockUseAuthStore,
}));

const idleMutation = {
  mutateAsync: vi.fn(),
  isPending: false,
  isError: false,
  isSuccess: false,
  mutate: vi.fn(),
} as const;

describe('IncomeEntriesPage', () => {
  beforeEach(() => {
    mockUseIncomeEntries.mockReset();
    mockUseDeleteIncomeEntry.mockReturnValue({ ...idleMutation } as unknown as DeleteResult);
    mockUseBuildings.mockReturnValue({ data: [], isLoading: false } as unknown as BuildingsResult);
    mockUseFinanceCategories.mockReturnValue({ data: [], isLoading: false } as unknown as CategoriesResult);
  });

  it('shows "Nova Receita" button for staff', async () => {
    mockUseAuthStore.mockReturnValue({ user: { is_staff: true } } as unknown);
    mockUseIncomeEntries.mockReturnValue({ isLoading: false, error: null, data: [] } as unknown as IncomeEntriesResult);

    renderWithProviders(<IncomeEntriesPage />, { queryClient: createTestQueryClient() });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Nova Receita/i })).toBeInTheDocument();
    });
  });

  it('hides "Nova Receita" button for non-staff', async () => {
    mockUseAuthStore.mockReturnValue({ user: { is_staff: false } } as unknown);
    mockUseIncomeEntries.mockReturnValue({ isLoading: false, error: null, data: [] } as unknown as IncomeEntriesResult);

    renderWithProviders(<IncomeEntriesPage />, { queryClient: createTestQueryClient() });

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /Nova Receita/i })).not.toBeInTheDocument();
    });
  });

  it('forwards the date filter to useIncomeEntries when it changes', async () => {
    mockUseAuthStore.mockReturnValue({ user: { is_staff: false } } as unknown);
    mockUseIncomeEntries.mockReturnValue({
      isLoading: false,
      error: null,
      data: [],
    } as unknown as IncomeEntriesResult);

    const { container } = renderWithProviders(<IncomeEntriesPage />, {
      queryClient: createTestQueryClient(),
    });

    // The two filter date inputs are plain <input type="date"> (the form modal is stubbed).
    const dateFrom = container.querySelectorAll('input[type="date"]')[0];
    if (!dateFrom) throw new Error('date filter input not found');
    fireEvent.change(dateFrom, { target: { value: '2026-06-01' } });

    await waitFor(() =>
      expect(mockUseIncomeEntries).toHaveBeenLastCalledWith(
        expect.objectContaining({ date_from: '2026-06-01' }),
      ),
    );
  });

  it('renders income entries in the table', async () => {
    mockUseAuthStore.mockReturnValue({ user: { is_staff: false } } as unknown);
    mockUseIncomeEntries.mockReturnValue({
      isLoading: false,
      error: null,
      data: [
        createMockIncomeEntry({ id: 1, description: 'Taxa condominial' }),
        createMockIncomeEntry({ id: 2, description: 'Multa por atraso', is_received: true }),
      ],
    } as unknown as IncomeEntriesResult);

    renderWithProviders(<IncomeEntriesPage />, { queryClient: createTestQueryClient() });

    // DataTable renders both a desktop table and a mobile cards view in DOM
    await waitFor(() => {
      expect(screen.getAllByText('Taxa condominial').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Multa por atraso').length).toBeGreaterThan(0);
    });
  });

  it('shows "Condomínio" for entries without a building', async () => {
    mockUseAuthStore.mockReturnValue({ user: { is_staff: false } } as unknown);
    mockUseIncomeEntries.mockReturnValue({
      isLoading: false,
      error: null,
      data: [createMockIncomeEntry({ id: 1, building: null })],
    } as unknown as IncomeEntriesResult);

    renderWithProviders(<IncomeEntriesPage />, { queryClient: createTestQueryClient() });

    await waitFor(() => {
      // Rendered in both desktop table and mobile cards — use getAllByText
      expect(screen.getAllByText('Condomínio').length).toBeGreaterThan(0);
    });
  });

  it('hides edit/delete actions for non-staff', async () => {
    mockUseAuthStore.mockReturnValue({ user: { is_staff: false } } as unknown);
    mockUseIncomeEntries.mockReturnValue({
      isLoading: false,
      error: null,
      data: [createMockIncomeEntry()],
    } as unknown as IncomeEntriesResult);

    renderWithProviders(<IncomeEntriesPage />, { queryClient: createTestQueryClient() });

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /Editar/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Excluir/i })).not.toBeInTheDocument();
    });
  });
});
