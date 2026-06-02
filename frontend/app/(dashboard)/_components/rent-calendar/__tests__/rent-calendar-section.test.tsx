import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { RentCalendarSection } from '../rent-calendar-section';
import * as rentCalendarHooks from '@/lib/api/hooks/use-rent-calendar';
import * as buildingsHooks from '@/lib/api/hooks/use-buildings';
import { formatMonthYear } from '@/lib/utils/formatters';
import type {
  RentCalendar,
  RentCalendarItem,
} from '@/lib/api/hooks/use-rent-calendar';

type RentCalendarResult = ReturnType<typeof rentCalendarHooks.useRentCalendar>;
type ToggleResult = ReturnType<typeof rentCalendarHooks.useToggleRentPayment>;
type BuildingsResult = ReturnType<typeof buildingsHooks.useBuildings>;

function makeQueryResult(overrides: Partial<RentCalendarResult>): RentCalendarResult {
  return {
    data: undefined,
    isLoading: false,
    isPending: false,
    isSuccess: false,
    isError: false,
    error: null,
    status: 'pending',
    fetchStatus: 'idle',
    dataUpdatedAt: 0,
    errorUpdatedAt: 0,
    failureCount: 0,
    failureReason: null,
    errorUpdateCount: 0,
    isFetched: false,
    isFetchedAfterMount: false,
    isFetching: false,
    isLoadingError: false,
    isPlaceholderData: false,
    isRefetchError: false,
    isRefetching: false,
    isStale: false,
    refetch: vi.fn(),
    ...overrides,
  } as unknown as RentCalendarResult;
}

function makeBuildingsResult(): BuildingsResult {
  return { data: [], isLoading: false } as unknown as BuildingsResult;
}

const mutateMock = vi.fn();

const idleMutation = {
  mutate: mutateMock,
  mutateAsync: vi.fn(),
  isPending: false,
  isSuccess: false,
  isError: false,
  error: null,
  data: undefined,
  reset: vi.fn(),
  status: 'idle',
  variables: undefined,
  context: undefined,
  failureCount: 0,
  failureReason: null,
  isIdle: true,
  isPaused: false,
  submittedAt: 0,
} as unknown as ToggleResult;

function makeItem(overrides: Partial<RentCalendarItem>): RentCalendarItem {
  return {
    lease_id: 12,
    tenant_name: 'João Silva',
    apartment_number: 101,
    building_number: '836',
    rental_value: '1500.00',
    is_paid: false,
    payment_date: null,
    is_overdue: false,
    day_passed: false,
    can_toggle: true,
    late_fee: '0.00',
    late_days: 0,
    ...overrides,
  };
}

const calendar: RentCalendar = {
  year: 2026,
  month: 6,
  today: '2026-06-15',
  next_due_date: '2026-06-15',
  days: [{ day: 15, date: '2026-06-15', weekday: 'Segunda', items: [makeItem({})] }],
  stats: {
    received_total: '4950.00',
    to_receive_total: '9650.00',
    expected_total: '14600.00',
    paid_count: 3,
    due_count: 9,
    overdue_count: 2,
    overdue_total_fee: '37.50',
    vacant_kitnets_count: 2,
    vacant_kitnets_value: '1600.00',
  },
};

describe('RentCalendarSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(buildingsHooks, 'useBuildings').mockReturnValue(makeBuildingsResult());
    vi.spyOn(rentCalendarHooks, 'useToggleRentPayment').mockReturnValue(idleMutation);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows a skeleton while loading', () => {
    vi.spyOn(rentCalendarHooks, 'useRentCalendar').mockReturnValue(
      makeQueryResult({ isLoading: true, isPending: true, fetchStatus: 'fetching' }),
    );
    const { container } = renderWithProviders(<RentCalendarSection />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders the day panel, grid and stats when data is present', async () => {
    vi.spyOn(rentCalendarHooks, 'useRentCalendar').mockReturnValue(
      makeQueryResult({ isSuccess: true, status: 'success', data: calendar }),
    );
    renderWithProviders(<RentCalendarSection />);

    await waitFor(() => {
      // Day panel (column 1): item rendered
      expect(screen.getByText('Apto 101 · Préd. 836')).toBeInTheDocument();
    });
    // Grid (column 2): weekday header
    expect(screen.getByText('Dom')).toBeInTheDocument();
    // Stats (column 3): unique "Recebido até hoje" card + the exact formatMonthYear label
    expect(screen.getByText('Recebido até hoje')).toBeInTheDocument();
    expect(screen.getAllByText(formatMonthYear(2026, 6)).length).toBeGreaterThan(0);
  });

  it('calls the toggle mutation with lease_id and reference_month of the loaded month', async () => {
    vi.spyOn(rentCalendarHooks, 'useRentCalendar').mockReturnValue(
      makeQueryResult({ isSuccess: true, status: 'success', data: calendar }),
    );
    renderWithProviders(<RentCalendarSection />);

    await waitFor(() => {
      expect(screen.getByRole('switch')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('switch'));

    expect(mutateMock).toHaveBeenCalledWith(
      { lease_id: 12, reference_month: '2026-06-01' },
      expect.anything(),
    );
  });
});
