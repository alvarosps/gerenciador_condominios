import { describe, it, expect, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import IncomeEntriesPage from '../page';
import { createMockIncomeEntry } from '@/tests/mocks/data/finances';

const API_BASE = 'http://localhost:8008/api';

// Real hooks (useIncomeEntries / useDeleteIncomeEntry / useBuildings / useFinanceCategories) hit
// MSW; the real auth store drives staff gating. Entry rows come from raw DRF payloads the hook
// parses with incomeEntrySchema.
function setStaff(isStaff: boolean) {
  useAuthStore.setState({
    user: { id: 1, email: 'a@b.c', first_name: 'A', last_name: 'B', is_staff: isStaff },
    isAuthenticated: true,
  });
}

function setEntries(entries: unknown[]) {
  server.use(http.get(`${API_BASE}/finances/income-entries/`, () => HttpResponse.json(entries)));
}

/** Spy the list GET; records the request URL so query params can be asserted. */
function spyList(entries: unknown[]) {
  const urls: string[] = [];
  server.use(
    http.get(`${API_BASE}/finances/income-entries/`, ({ request }) => {
      urls.push(request.url);
      return HttpResponse.json(entries);
    })
  );
  return urls;
}

describe('IncomeEntriesPage', () => {
  beforeEach(() => {
    setStaff(false);
    setEntries([]);
  });

  it('shows "Nova Receita" button for staff', async () => {
    setStaff(true);
    setEntries([]);

    const { queryClient } = renderWithProviders(<IncomeEntriesPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Nova Receita/i })).toBeInTheDocument();
    });

    await waitForQueriesToSettle(queryClient);
  });

  it('hides "Nova Receita" button for non-staff', async () => {
    setStaff(false);
    setEntries([]);

    const { queryClient } = renderWithProviders(<IncomeEntriesPage />);

    await waitFor(() => {
      expect(screen.getByText('Receitas do Condomínio')).toBeInTheDocument();
    });
    expect(screen.queryByRole('button', { name: /Nova Receita/i })).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('forwards the date filter to the list request when it changes', async () => {
    setStaff(false);
    const urls = spyList([]);

    const { container, queryClient } = renderWithProviders(<IncomeEntriesPage />);

    await waitFor(() => expect(urls.length).toBeGreaterThan(0));

    // The two filter date inputs are plain <input type="date">.
    const dateFrom = container.querySelectorAll('input[type="date"]')[0];
    if (!dateFrom) throw new Error('date filter input not found');
    fireEvent.change(dateFrom, { target: { value: '2026-06-01' } });

    await waitFor(() => expect(urls.some((u) => u.includes('date_from=2026-06-01'))).toBe(true));

    await waitForQueriesToSettle(queryClient);
  });

  it('renders income entries in the table', async () => {
    setStaff(false);
    setEntries([
      createMockIncomeEntry({ id: 1, description: 'Taxa condominial' }),
      createMockIncomeEntry({ id: 2, description: 'Multa por atraso', is_received: true }),
    ]);

    const { queryClient } = renderWithProviders(<IncomeEntriesPage />);

    // DataTable renders both a desktop table and a mobile cards view in DOM
    await waitFor(() => {
      expect(screen.getAllByText('Taxa condominial').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Multa por atraso').length).toBeGreaterThan(0);
    });

    await waitForQueriesToSettle(queryClient);
  });

  it('shows "Condomínio" for entries without a building', async () => {
    setStaff(false);
    setEntries([createMockIncomeEntry({ id: 1, building: null })]);

    const { queryClient } = renderWithProviders(<IncomeEntriesPage />);

    await waitFor(() => {
      // Rendered in both desktop table and mobile cards — use getAllByText
      expect(screen.getAllByText('Condomínio').length).toBeGreaterThan(0);
    });

    await waitForQueriesToSettle(queryClient);
  });

  it('hides edit/delete actions for non-staff', async () => {
    setStaff(false);
    setEntries([createMockIncomeEntry()]);

    const { queryClient } = renderWithProviders(<IncomeEntriesPage />);

    await waitFor(() => {
      expect(screen.getAllByText('Receita extra').length).toBeGreaterThan(0);
    });
    expect(screen.queryByRole('button', { name: /Editar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Excluir/i })).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });
});
