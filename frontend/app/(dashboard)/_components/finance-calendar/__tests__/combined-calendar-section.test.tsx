import { describe, it, expect, vi, beforeAll, beforeEach, afterEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import { createMockBillExit, createMockCombinedCalendar } from '@/tests/mocks/data/finances';
import { CombinedCalendarSection } from '../combined-calendar-section';

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

function setCombinedCalendarResponse(overrides: Parameters<typeof createMockCombinedCalendar>[0]) {
  server.use(
    http.get(`${API_BASE}/finances/finance-dashboard/combined_calendar/`, () =>
      HttpResponse.json(createMockCombinedCalendar(overrides))
    )
  );
}

// combined_calendar is uncached and re-requested on every navigation — capture the params of the
// latest request so navigation/filter assertions inspect the real query string.
function captureCombinedCalendarParams() {
  const captured: { year: number | null; month: number | null; building_id: number | null } = {
    year: null,
    month: null,
    building_id: null,
  };
  server.use(
    http.get(`${API_BASE}/finances/finance-dashboard/combined_calendar/`, ({ request }) => {
      const params = new URL(request.url).searchParams;
      captured.year = Number(params.get('year') ?? '0');
      captured.month = Number(params.get('month') ?? '0');
      const buildingId = params.get('building_id');
      captured.building_id = buildingId ? Number(buildingId) : null;
      return HttpResponse.json(
        createMockCombinedCalendar({
          year: captured.year,
          month: captured.month,
        })
      );
    })
  );
  return captured;
}

describe('CombinedCalendarSection', () => {
  beforeEach(() => {
    // The component defaults its selected month/day to the real system clock,
    // while every fixture below is anchored to 2026-06-07 — pin the clock so
    // the default selection lands on the day the fixtures expect. Only `Date`
    // is faked (not timers) so RTL's async `findBy*`/`waitFor` polling and
    // userEvent's internal delays keep working normally.
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2026, 5, 7));
    useAuthStore.setState({
      user: { id: 1, email: 'a@b.c', first_name: 'A', last_name: 'B', is_staff: true },
      isAuthenticated: true,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders a skeleton while loading', async () => {
    server.use(
      http.get(`${API_BASE}/finances/finance-dashboard/combined_calendar/`, async () => {
        await new Promise((resolve) => setTimeout(resolve, 50));
        return HttpResponse.json(createMockCombinedCalendar());
      })
    );
    const { container, queryClient } = renderWithProviders(<CombinedCalendarSection />);
    expect(container.querySelectorAll('[class*="animate-pulse"]').length).toBeGreaterThan(0);
    await waitForQueriesToSettle(queryClient);
  });

  it('renders the day panel, the grid and the stats column with data (1 assertion per column)', async () => {
    setCombinedCalendarResponse({
      days: [
        {
          day: 7,
          date: '2026-06-07',
          weekday: 'Domingo',
          rent_entries: [],
          bill_exits: [createMockBillExit({ description: 'Conta de Luz' })],
        },
      ],
    });
    const { queryClient } = renderWithProviders(<CombinedCalendarSection />);

    // Column 1 (day panel)
    expect(await screen.findByText('Aluguéis (entradas)')).toBeInTheDocument();
    // Column 2 (grid)
    expect(screen.getAllByRole('gridcell').length).toBeGreaterThan(0);
    // Column 3 (stats)
    expect(screen.getByText('A pagar (mês)')).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('passes the new month to the combined_calendar request when navigating', async () => {
    const captured = captureCombinedCalendarParams();
    const { queryClient } = renderWithProviders(<CombinedCalendarSection />);

    await screen.findByText('Calendário do Condomínio');
    await waitFor(() => expect(captured.month).toBe(6));

    await userEvent.click(screen.getByRole('button', { name: /próximo mês/i }), {
      advanceTimers: vi.advanceTimersByTime,
    });

    await waitFor(() => expect(captured.month).toBe(7));
    await waitForQueriesToSettle(queryClient);
  });

  it('passes the building_id to the combined_calendar request when a building filter is selected', async () => {
    const captured = captureCombinedCalendarParams();
    const user = userEvent.setup({ pointerEventsCheck: 0, advanceTimers: vi.advanceTimersByTime });
    const { queryClient } = renderWithProviders(<CombinedCalendarSection />);

    await screen.findByText('Calendário do Condomínio');
    await waitFor(() => expect(captured.building_id).toBeNull());

    await user.click(screen.getByRole('combobox'));
    const option = await screen.findByRole('option', { name: 'Edifício São Paulo' });
    await user.click(option);

    await waitFor(() => expect(typeof captured.building_id).toBe('number'));
    await waitForQueriesToSettle(queryClient);
  });

  it('opens the payment dialog when a bill toggle is used', async () => {
    setCombinedCalendarResponse({
      days: [
        {
          day: 7,
          date: '2026-06-07',
          weekday: 'Domingo',
          rent_entries: [],
          bill_exits: [createMockBillExit({ bill_id: 9, description: 'Conta de Luz' })],
        },
      ],
    });
    const { queryClient } = renderWithProviders(<CombinedCalendarSection />);

    await userEvent.click(await screen.findByRole('switch'), {
      advanceTimers: vi.advanceTimersByTime,
    });

    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/Pagar conta/i)).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });
});
