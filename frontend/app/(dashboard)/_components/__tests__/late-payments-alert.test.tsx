import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/tests/test-utils';
import { LatePaymentsAlert } from '../late-payments-alert';
import * as dashboardHooks from '@/lib/api/hooks/use-dashboard';
import * as rentCalendarHooks from '@/lib/api/hooks/use-rent-calendar';

type LatePaymentsResult = ReturnType<typeof dashboardHooks.useDashboardLatePayments>;
type ToggleResult = ReturnType<typeof rentCalendarHooks.useToggleRentPayment>;

function makeQueryResult(overrides: Partial<LatePaymentsResult>): LatePaymentsResult {
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
  } as LatePaymentsResult;
}

function makeIdleToggle(overrides: Partial<ToggleResult> = {}): ToggleResult {
  return {
    mutate: vi.fn(),
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
    ...overrides,
  } as unknown as ToggleResult;
}

const lateLeasesData: NonNullable<LatePaymentsResult['data']> = {
  total_late_leases: 1,
  total_late_fees: '250.00',
  average_late_days: 5,
  late_leases: [
    {
      lease_id: 1,
      apartment_number: 101,
      building_number: '836',
      tenant_name: 'João Silva',
      rental_value: '1200.00',
      due_day: 5,
      late_days: 10,
      late_fee: '250.00',
      last_payment_date: '2024-03-05',
    },
  ],
};

describe('LatePaymentsAlert', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders nothing while loading', () => {
    vi.spyOn(dashboardHooks, 'useDashboardLatePayments').mockReturnValue(
      makeQueryResult({ isLoading: true, isPending: true, fetchStatus: 'fetching' }),
    );
    vi.spyOn(rentCalendarHooks, 'useToggleRentPayment').mockReturnValue(makeIdleToggle());

    const { container } = renderWithProviders(<LatePaymentsAlert />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows success message when no late payments', async () => {
    vi.spyOn(dashboardHooks, 'useDashboardLatePayments').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isSuccess: true,
        isFetched: true,
        status: 'success',
        data: {
          total_late_leases: 0,
          total_late_fees: '0.00',
          average_late_days: 0,
          late_leases: [],
        },
      }),
    );
    vi.spyOn(rentCalendarHooks, 'useToggleRentPayment').mockReturnValue(makeIdleToggle());

    renderWithProviders(<LatePaymentsAlert />);

    await waitFor(() => {
      expect(screen.getByText(/parabéns/i)).toBeInTheDocument();
      expect(screen.getByText(/não há pagamentos em atraso/i)).toBeInTheDocument();
    });
  });

  it('shows accordion with late leases when there are late payments', async () => {
    vi.spyOn(dashboardHooks, 'useDashboardLatePayments').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isSuccess: true,
        isFetched: true,
        status: 'success',
        data: lateLeasesData,
      }),
    );
    vi.spyOn(rentCalendarHooks, 'useToggleRentPayment').mockReturnValue(makeIdleToggle());

    renderWithProviders(<LatePaymentsAlert />);

    await waitFor(() => {
      expect(screen.getByText('Pagamentos em Atraso')).toBeInTheDocument();
    });
  });

  it('clicking "Pago" triggers the unified toggle with lease_id and current-month reference', async () => {
    const mutate = vi.fn();
    vi.spyOn(dashboardHooks, 'useDashboardLatePayments').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isSuccess: true,
        isFetched: true,
        status: 'success',
        data: lateLeasesData,
      }),
    );
    vi.spyOn(rentCalendarHooks, 'useToggleRentPayment').mockReturnValue(
      makeIdleToggle({ mutate }),
    );

    const user = userEvent.setup();
    renderWithProviders(<LatePaymentsAlert />);

    await user.click(await screen.findByRole('button', { name: /pagamentos em atraso/i }));
    await user.click(await screen.findByRole('button', { name: /^pago$/i }));

    expect(mutate).toHaveBeenCalledTimes(1);
    const [variables] = mutate.mock.calls[0] as [
      { lease_id: number; reference_month: string },
      ...unknown[],
    ];
    expect(variables.lease_id).toBe(1);
    expect(variables.reference_month).toMatch(/^\d{4}-\d{2}-01$/);
  });

  it('shows success message when data is undefined (no payments loaded)', async () => {
    vi.spyOn(dashboardHooks, 'useDashboardLatePayments').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isSuccess: true,
        status: 'success',
        data: undefined,
      }),
    );
    vi.spyOn(rentCalendarHooks, 'useToggleRentPayment').mockReturnValue(makeIdleToggle());

    renderWithProviders(<LatePaymentsAlert />);

    await waitFor(() => {
      expect(screen.getByText(/não há pagamentos em atraso/i)).toBeInTheDocument();
    });
  });
});
