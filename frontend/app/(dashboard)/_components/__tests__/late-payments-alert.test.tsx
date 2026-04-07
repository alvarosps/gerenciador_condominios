import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { LatePaymentsAlert } from '../late-payments-alert';
import * as dashboardHooks from '@/lib/api/hooks/use-dashboard';

type LatePaymentsResult = ReturnType<typeof dashboardHooks.useDashboardLatePayments>;
type MarkRentPaidResult = ReturnType<typeof dashboardHooks.useMarkRentPaid>;

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

const idleMutation = {
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
} as unknown as MarkRentPaidResult;

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
    vi.spyOn(dashboardHooks, 'useMarkRentPaid').mockReturnValue(idleMutation);

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
    vi.spyOn(dashboardHooks, 'useMarkRentPaid').mockReturnValue(idleMutation);

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
        data: {
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
        },
      }),
    );
    vi.spyOn(dashboardHooks, 'useMarkRentPaid').mockReturnValue(idleMutation);

    renderWithProviders(<LatePaymentsAlert />);

    await waitFor(() => {
      expect(screen.getByText('Pagamentos em Atraso')).toBeInTheDocument();
    });
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
    vi.spyOn(dashboardHooks, 'useMarkRentPaid').mockReturnValue(idleMutation);

    renderWithProviders(<LatePaymentsAlert />);

    await waitFor(() => {
      expect(screen.getByText(/não há pagamentos em atraso/i)).toBeInTheDocument();
    });
  });
});
