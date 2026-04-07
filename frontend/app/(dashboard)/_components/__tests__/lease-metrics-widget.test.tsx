import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { LeaseMetricsWidget } from '../lease-metrics-widget';
import * as dashboardHooks from '@/lib/api/hooks/use-dashboard';

type LeaseMetricsResult = ReturnType<typeof dashboardHooks.useDashboardLeaseMetrics>;

function makeQueryResult(overrides: Partial<LeaseMetricsResult>): LeaseMetricsResult {
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
  } as LeaseMetricsResult;
}

describe('LeaseMetricsWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows loading state while fetching', () => {
    vi.spyOn(dashboardHooks, 'useDashboardLeaseMetrics').mockReturnValue(
      makeQueryResult({ isLoading: true, isPending: true, fetchStatus: 'fetching' }),
    );

    renderWithProviders(<LeaseMetricsWidget />);

    expect(screen.getByText('Métricas de Locações')).toBeInTheDocument();
    expect(screen.queryByText('Locações Ativas')).not.toBeInTheDocument();
  });

  it('shows error state when API call fails', async () => {
    vi.spyOn(dashboardHooks, 'useDashboardLeaseMetrics').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isError: true,
        status: 'error',
        error: new Error('Server error'),
      }),
    );

    renderWithProviders(<LeaseMetricsWidget />);

    await waitFor(() => {
      expect(screen.getByText(/erro ao carregar métricas/i)).toBeInTheDocument();
    });
  });

  it('renders metric data when loaded', async () => {
    vi.spyOn(dashboardHooks, 'useDashboardLeaseMetrics').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isSuccess: true,
        isFetched: true,
        status: 'success',
        data: {
          total_leases: 10,
          active_leases: 8,
          inactive_leases: 2,
          contracts_generated: 7,
          contracts_pending: 1,
          expiring_soon: 2,
          expired_leases: 0,
          avg_validity_months: 12,
        },
      }),
    );

    renderWithProviders(<LeaseMetricsWidget />);

    await waitFor(() => {
      expect(screen.getByText('Locações Ativas')).toBeInTheDocument();
      expect(screen.getByText('Expirando em Breve')).toBeInTheDocument();
      expect(screen.getByText('Locações Expiradas')).toBeInTheDocument();
      expect(screen.getByText('Contratos Pendentes')).toBeInTheDocument();
    });
  });

  it('renders nothing when data is undefined', () => {
    vi.spyOn(dashboardHooks, 'useDashboardLeaseMetrics').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isSuccess: true,
        status: 'success',
        data: undefined,
      }),
    );

    const { container } = renderWithProviders(<LeaseMetricsWidget />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows total leases count', async () => {
    vi.spyOn(dashboardHooks, 'useDashboardLeaseMetrics').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isSuccess: true,
        isFetched: true,
        status: 'success',
        data: {
          total_leases: 15,
          active_leases: 12,
          inactive_leases: 3,
          contracts_generated: 10,
          contracts_pending: 2,
          expiring_soon: 3,
          expired_leases: 1,
          avg_validity_months: 12,
        },
      }),
    );

    renderWithProviders(<LeaseMetricsWidget />);

    await waitFor(() => {
      expect(screen.getByText('Total de Contratos:')).toBeInTheDocument();
      expect(screen.getByText('15')).toBeInTheDocument();
    });
  });
});
