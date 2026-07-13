import { describe, it, expect, vi, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor, fireEvent, within } from '@testing-library/react';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import MonthClosePage from '../page';
import { createMockCondoMonthClose } from '@/tests/mocks/data/finances';
import { formatReferenceMonth } from '@/lib/utils/finances';
import { toast } from 'sonner';

const API_BASE = 'http://localhost:8008/api';

/** Previous calendar month relative to "now", mirroring the page's own default. */
function previousMonth(): { year: number; month: number } {
  const now = new Date();
  const year = now.getMonth() === 0 ? now.getFullYear() - 1 : now.getFullYear();
  const month = now.getMonth() === 0 ? 12 : now.getMonth();
  return { year, month };
}

function referenceMonthLabel(year: number, month: number): string {
  return formatReferenceMonth(`${year}-${String(month).padStart(2, '0')}-01`);
}

// Real hooks (useCondoMonthCloses / useCloseMonth / useReopenMonth) hit MSW; the real auth store
// drives staff gating. `toast` is the global sonner mock from tests/setup.ts.
function setStaff(isStaff: boolean) {
  useAuthStore.setState({
    user: { id: 1, email: 'a@b.c', first_name: 'A', last_name: 'B', is_staff: isStaff },
    isAuthenticated: true,
  });
}

function setCloses(closes: unknown[]) {
  server.use(http.get(`${API_BASE}/finances/condo-month-closes/`, () => HttpResponse.json(closes)));
}

function spyClose() {
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.post(`${API_BASE}/finances/condo-month-closes/close/`, async ({ request }) => {
      bodies.push((await request.json()) as Record<string, unknown>);
      return HttpResponse.json(
        createMockCondoMonthClose({ reference_month: '2026-05-01', status: 'closed' })
      );
    })
  );
  return bodies;
}

describe('MonthClosePage', () => {
  beforeEach(() => {
    setStaff(false);
    vi.mocked(toast.success).mockReset();
    vi.mocked(toast.error).mockReset();
  });

  it('renders the page title', async () => {
    setCloses([]);

    const { queryClient } = renderWithProviders(<MonthClosePage />);

    await waitFor(() => {
      expect(screen.getByText('Fechamento Mensal')).toBeInTheDocument();
    });

    await waitForQueriesToSettle(queryClient);
  });

  it('renders month closes in the table', async () => {
    setCloses([
      createMockCondoMonthClose({ id: 1, reference_month: '2026-05-01', status: 'closed' }),
      createMockCondoMonthClose({ id: 2, reference_month: '2026-04-01', status: 'open' }),
    ]);

    const { queryClient } = renderWithProviders(<MonthClosePage />);

    await waitFor(() => {
      // DataTable renders both desktop table and mobile cards views
      expect(screen.getAllByText(/maio de 2026/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/abril de 2026/i).length).toBeGreaterThan(0);
    });

    await waitForQueriesToSettle(queryClient);
  });

  it('shows "Fechar" button for open months (staff only)', async () => {
    setStaff(true);
    setCloses([createMockCondoMonthClose({ id: 1, status: 'open' })]);

    const { queryClient } = renderWithProviders(<MonthClosePage />);

    // DataTable renders both desktop and mobile views — use getAllByRole
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: 'Fechar' }).length).toBeGreaterThan(0);
    });

    await waitForQueriesToSettle(queryClient);
  });

  it('shows "Reabrir" button for closed months (staff only)', async () => {
    setStaff(true);
    setCloses([createMockCondoMonthClose({ id: 1, status: 'closed' })]);

    const { queryClient } = renderWithProviders(<MonthClosePage />);

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: 'Reabrir' }).length).toBeGreaterThan(0);
    });

    await waitForQueriesToSettle(queryClient);
  });

  it('hides action buttons for non-staff', async () => {
    setStaff(false);
    setCloses([
      createMockCondoMonthClose({ id: 1, status: 'open' }),
      createMockCondoMonthClose({ id: 2, status: 'closed' }),
    ]);

    const { queryClient } = renderWithProviders(<MonthClosePage />);

    // Wait for data to load (the status badge renders the month label), then assert no actions.
    await waitFor(() => {
      expect(screen.getAllByText(/maio de 2026/i).length).toBeGreaterThan(0);
    });
    expect(screen.queryByRole('button', { name: 'Fechar' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Reabrir' })).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('opens confirm dialog when clicking close', async () => {
    setStaff(true);
    setCloses([
      createMockCondoMonthClose({ id: 1, reference_month: '2026-05-01', status: 'open' }),
    ]);

    const { queryClient } = renderWithProviders(<MonthClosePage />);

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: 'Fechar' }).length).toBeGreaterThan(0);
    });

    // Click the first instance (both desktop and mobile render the row's "Fechar" button)
    const [firstButton] = screen.getAllByRole('button', { name: 'Fechar' });
    if (!firstButton) throw new Error('Fechar button not found');
    fireEvent.click(firstButton);

    await waitFor(() => {
      expect(screen.getByText(/Fechar o mês congela/i)).toBeInTheDocument();
    });

    await waitForQueriesToSettle(queryClient);
  });

  it('confirming a close derives {year,month} by split, posts to the API and toasts success', async () => {
    setStaff(true);
    const bodies = spyClose();
    setCloses([
      createMockCondoMonthClose({ id: 1, reference_month: '2026-05-01', status: 'open' }),
    ]);

    renderWithProviders(<MonthClosePage />);

    const [openBtn] = await screen.findAllByRole('button', { name: 'Fechar' });
    if (!openBtn) throw new Error('open button not found');
    fireEvent.click(openBtn);
    const dialog = await screen.findByRole('alertdialog');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Fechar mês' }));

    // 2026-05-01 → {year:2026, month:5} via split (NOT new Date) — no off-by-one/TZ shift.
    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({ year: 2026, month: 5 });
    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('Mês fechado com sucesso'));
  });

  it('surfaces the backend PT error (chronological gap) via toast.error on reject', async () => {
    setStaff(true);
    server.use(
      http.post(`${API_BASE}/finances/condo-month-closes/close/`, () =>
        HttpResponse.json(
          { error: 'Feche os meses anteriores antes de fechar este mês.' },
          { status: 400 }
        )
      )
    );
    setCloses([
      createMockCondoMonthClose({ id: 1, reference_month: '2026-05-01', status: 'open' }),
    ]);

    renderWithProviders(<MonthClosePage />);

    const [openBtn] = await screen.findAllByRole('button', { name: 'Fechar' });
    if (!openBtn) throw new Error('open button not found');
    fireEvent.click(openBtn);
    const dialog = await screen.findByRole('alertdialog');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Fechar mês' }));

    // The front never validates chronology — it shows the server's PT message verbatim (§18).
    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        'Feche os meses anteriores antes de fechar este mês.'
      )
    );
  });

  it('shows the header month-close control for staff, defaulting to the previous month', async () => {
    setStaff(true);
    setCloses([]);
    const { year, month } = previousMonth();

    renderWithProviders(<MonthClosePage />);

    expect(await screen.findByText(referenceMonthLabel(year, month))).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Fechar mês' })).toBeInTheDocument();
  });

  it('does not show the header month-close control for non-staff', async () => {
    setStaff(false);
    setCloses([]);

    renderWithProviders(<MonthClosePage />);

    await waitFor(() => {
      expect(screen.getByText('Fechamento Mensal')).toBeInTheDocument();
    });
    expect(screen.queryByRole('button', { name: 'Fechar mês' })).not.toBeInTheDocument();
  });

  it('opens the confirm dialog for a month with no existing record (first-time close)', async () => {
    setStaff(true);
    setCloses([]);
    const { year, month } = previousMonth();

    renderWithProviders(<MonthClosePage />);

    const headerButton = await screen.findByRole('button', { name: 'Fechar mês' });
    fireEvent.click(headerButton);

    const dialog = await screen.findByRole('alertdialog');
    expect(within(dialog).getByRole('heading')).toHaveTextContent(referenceMonthLabel(year, month));
  });

  it('closing via the header control for a month with no record posts {year,month} for that competence', async () => {
    setStaff(true);
    const bodies = spyClose();
    setCloses([]);
    const { year, month } = previousMonth();

    renderWithProviders(<MonthClosePage />);

    const headerButton = await screen.findByRole('button', { name: 'Fechar mês' });
    fireEvent.click(headerButton);
    const dialog = await screen.findByRole('alertdialog');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Fechar mês' }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({ year, month });
  });
});
