import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { RentAdjustmentAlerts } from '../rent-adjustment-alerts';
import * as rentAdjustmentHooks from '@/lib/api/hooks/use-rent-adjustments';
import type { RentAdjustmentAlert } from '@/lib/schemas/rent-adjustment.schema';

type RentAdjustmentAlertsResult = ReturnType<typeof rentAdjustmentHooks.useRentAdjustmentAlerts>;
type ApplyRentAdjustmentResult = ReturnType<typeof rentAdjustmentHooks.useApplyRentAdjustment>;

function makeQueryResult(overrides: Partial<RentAdjustmentAlertsResult>): RentAdjustmentAlertsResult {
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
  } as RentAdjustmentAlertsResult;
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
} as unknown as ApplyRentAdjustmentResult;

const mockAlert: RentAdjustmentAlert = {
  lease_id: 1,
  apartment: 'Prédio 836 - Apto 101',
  tenant: 'João Silva',
  rental_value: 1200,
  new_value: 1285.2,
  ipca_percentage: 7.1,
  ipca_source: 'ipca',
  last_rent_increase_date: '2024-01-01',
  eligible_date: '2025-01-01',
  days_until: -30,
  status: 'overdue',
  prepaid_warning: false,
  last_adjustment: null,
};

describe('RentAdjustmentAlerts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders nothing while loading', () => {
    vi.spyOn(rentAdjustmentHooks, 'useRentAdjustmentAlerts').mockReturnValue(
      makeQueryResult({ isLoading: true, isPending: true, fetchStatus: 'fetching' }),
    );
    vi.spyOn(rentAdjustmentHooks, 'useApplyRentAdjustment').mockReturnValue(idleMutation);

    const { container } = renderWithProviders(<RentAdjustmentAlerts />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows success message when no pending adjustments', async () => {
    vi.spyOn(rentAdjustmentHooks, 'useRentAdjustmentAlerts').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isSuccess: true,
        isFetched: true,
        status: 'success',
        data: { alerts: [], ipcaLatestMonth: null },
      }),
    );
    vi.spyOn(rentAdjustmentHooks, 'useApplyRentAdjustment').mockReturnValue(idleMutation);

    renderWithProviders(<RentAdjustmentAlerts />);

    await waitFor(() => {
      expect(screen.getByText(/nenhum reajuste pendente/i)).toBeInTheDocument();
    });
  });

  it('shows accordion with pending alerts', async () => {
    vi.spyOn(rentAdjustmentHooks, 'useRentAdjustmentAlerts').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isSuccess: true,
        isFetched: true,
        status: 'success',
        data: {
          alerts: [mockAlert],
          ipcaLatestMonth: '2025-01-01',
        },
      }),
    );
    vi.spyOn(rentAdjustmentHooks, 'useApplyRentAdjustment').mockReturnValue(idleMutation);

    renderWithProviders(<RentAdjustmentAlerts />);

    await waitFor(() => {
      expect(screen.getByText('Reajustes Pendentes')).toBeInTheDocument();
    });
  });

  it('shows success message when data is undefined (no alerts loaded)', async () => {
    vi.spyOn(rentAdjustmentHooks, 'useRentAdjustmentAlerts').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isSuccess: true,
        status: 'success',
        data: undefined,
      }),
    );
    vi.spyOn(rentAdjustmentHooks, 'useApplyRentAdjustment').mockReturnValue(idleMutation);

    renderWithProviders(<RentAdjustmentAlerts />);

    await waitFor(() => {
      expect(screen.getByText(/nenhum reajuste pendente/i)).toBeInTheDocument();
    });
  });
});
