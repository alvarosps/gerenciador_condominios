import { describe, it, expect, vi, beforeAll, beforeEach, afterEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/tests/test-utils';
import { useAuthStore } from '@/store/auth-store';
import {
  createMockBillExit,
  createMockCombinedCalendar,
  createMockOverdueResponse,
} from '@/tests/mocks/data/finances';
import { CombinedCalendarSection } from '../combined-calendar-section';
import * as calendarHooks from '@/lib/api/hooks/use-combined-calendar';
import type { UseQueryResult } from '@tanstack/react-query';
import type {
  CombinedCalendar,
  OverdueBillsResponse,
} from '@/lib/api/hooks/use-combined-calendar';

vi.mock('@/lib/api/hooks/use-combined-calendar', async (importOriginal) => {
  const actual = await importOriginal<typeof calendarHooks>();
  return { ...actual, useCombinedCalendar: vi.fn(), useOverdueBills: vi.fn() };
});

// Test-fixture carve-out: building a TanStack query result shape is infeasible without an assertion.
function makeQueryResult<T>(data: T | undefined, isLoading: boolean): UseQueryResult<T> {
  return {
    data,
    isLoading,
    isPending: isLoading,
    isSuccess: !isLoading,
    error: null,
    isError: false,
    status: isLoading ? 'pending' : 'success',
  } as unknown as UseQueryResult<T>;
}

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

function mockCalendar(calendar: CombinedCalendar | undefined, isLoading = false) {
  vi.mocked(calendarHooks.useCombinedCalendar).mockReturnValue(
    makeQueryResult<CombinedCalendar>(calendar, isLoading),
  );
  vi.mocked(calendarHooks.useOverdueBills).mockReturnValue(
    makeQueryResult<OverdueBillsResponse>(
      { ...createMockOverdueResponse(), bills: [] },
      false,
    ),
  );
}

describe('CombinedCalendarSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: { id: 1, email: 'a@b.c', first_name: 'A', last_name: 'B', is_staff: true },
      isAuthenticated: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders a skeleton while loading', () => {
    mockCalendar(undefined, true);
    const { container } = renderWithProviders(<CombinedCalendarSection />);
    expect(container.querySelectorAll('[class*="animate-pulse"]').length).toBeGreaterThan(0);
  });

  it('renders the day panel, the grid and the stats column with data (1 assertion per column)', async () => {
    mockCalendar(
      createMockCombinedCalendar({
        days: [
          {
            day: 7,
            date: '2026-06-07',
            weekday: 'Domingo',
            rent_entries: [],
            bill_exits: [createMockBillExit({ description: 'Conta de Luz' })],
          },
        ],
      }),
    );
    renderWithProviders(<CombinedCalendarSection />);

    // Column 1 (day panel)
    expect(await screen.findByText('Aluguéis (entradas)')).toBeInTheDocument();
    // Column 2 (grid)
    expect(screen.getAllByRole('gridcell').length).toBeGreaterThan(0);
    // Column 3 (stats)
    expect(screen.getByText('A pagar (mês)')).toBeInTheDocument();
  });

  it('passes the new month to useCombinedCalendar when navigating', async () => {
    mockCalendar(createMockCombinedCalendar({ year: 2026, month: 6 }));
    renderWithProviders(<CombinedCalendarSection />);

    await screen.findByText('Calendário do Condomínio');
    vi.mocked(calendarHooks.useCombinedCalendar).mockClear();

    await userEvent.click(screen.getByRole('button', { name: /próximo mês/i }));

    await waitFor(() => {
      const lastCall = vi.mocked(calendarHooks.useCombinedCalendar).mock.calls.at(-1);
      expect(lastCall?.[1]).toBe(7);
    });
  });

  it('passes the building_id to useCombinedCalendar when a building filter is selected', async () => {
    mockCalendar(createMockCombinedCalendar());
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderWithProviders(<CombinedCalendarSection />);

    await screen.findByText('Calendário do Condomínio');

    await user.click(screen.getByRole('combobox'));
    const option = await screen.findByRole('option', { name: 'Edifício São Paulo' });
    vi.mocked(calendarHooks.useCombinedCalendar).mockClear();
    await user.click(option);

    await waitFor(() => {
      const lastCall = vi.mocked(calendarHooks.useCombinedCalendar).mock.calls.at(-1);
      expect(typeof lastCall?.[2]).toBe('number');
    });
  });

  it('opens the payment dialog when a bill toggle is used', async () => {
    mockCalendar(
      createMockCombinedCalendar({
        days: [
          {
            day: 7,
            date: '2026-06-07',
            weekday: 'Domingo',
            rent_entries: [],
            bill_exits: [createMockBillExit({ bill_id: 9, description: 'Conta de Luz' })],
          },
        ],
      }),
    );
    renderWithProviders(<CombinedCalendarSection />);

    await userEvent.click(await screen.findByRole('switch'));

    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/Pagar conta/i)).toBeInTheDocument();
  });
});
