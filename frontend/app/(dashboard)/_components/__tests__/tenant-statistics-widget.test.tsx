import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { TenantStatisticsWidget } from '../tenant-statistics-widget';
import * as dashboardHooks from '@/lib/api/hooks/use-dashboard';

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  PieChart: ({ children }: { children: React.ReactNode }) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => null,
  Cell: () => null,
  Tooltip: () => null,
  Legend: () => null,
}));

type TenantStatisticsResult = ReturnType<typeof dashboardHooks.useDashboardTenantStatistics>;

function makeQueryResult(overrides: Partial<TenantStatisticsResult>): TenantStatisticsResult {
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
  } as TenantStatisticsResult;
}

describe('TenantStatisticsWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows loading state while fetching', () => {
    vi.spyOn(dashboardHooks, 'useDashboardTenantStatistics').mockReturnValue(
      makeQueryResult({ isLoading: true, isPending: true, fetchStatus: 'fetching' }),
    );

    renderWithProviders(<TenantStatisticsWidget />);

    expect(screen.getByText('Estatísticas de Inquilinos')).toBeInTheDocument();
    expect(screen.queryByText('Total de Inquilinos')).not.toBeInTheDocument();
  });

  it('shows error state when API call fails', async () => {
    vi.spyOn(dashboardHooks, 'useDashboardTenantStatistics').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isError: true,
        status: 'error',
        error: new Error('Server error'),
      }),
    );

    renderWithProviders(<TenantStatisticsWidget />);

    await waitFor(() => {
      expect(screen.getByText(/erro ao carregar estatísticas/i)).toBeInTheDocument();
    });
  });

  it('renders statistics when loaded', async () => {
    vi.spyOn(dashboardHooks, 'useDashboardTenantStatistics').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isSuccess: true,
        isFetched: true,
        status: 'success',
        data: {
          total_tenants: 20,
          individual_tenants: 15,
          company_tenants: 5,
          person_tenants: 15,
          tenants_with_dependents: 8,
          tenants_with_furniture: 10,
          total_dependents: 12,
          avg_dependents: 1.5,
          marital_status_distribution: [],
        },
      }),
    );

    renderWithProviders(<TenantStatisticsWidget />);

    await waitFor(() => {
      expect(screen.getByText('Total de Inquilinos')).toBeInTheDocument();
      expect(screen.getByText('Com Dependentes')).toBeInTheDocument();
    });
  });

  it('displays total tenants count', async () => {
    vi.spyOn(dashboardHooks, 'useDashboardTenantStatistics').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isSuccess: true,
        isFetched: true,
        status: 'success',
        data: {
          total_tenants: 25,
          individual_tenants: 20,
          company_tenants: 5,
          person_tenants: 20,
          tenants_with_dependents: 10,
          tenants_with_furniture: 12,
          total_dependents: 15,
          avg_dependents: 1.5,
          marital_status_distribution: [],
        },
      }),
    );

    renderWithProviders(<TenantStatisticsWidget />);

    await waitFor(() => {
      expect(screen.getByText('25')).toBeInTheDocument();
    });
  });

  it('renders pie chart when data loaded', async () => {
    vi.spyOn(dashboardHooks, 'useDashboardTenantStatistics').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isSuccess: true,
        isFetched: true,
        status: 'success',
        data: {
          total_tenants: 10,
          individual_tenants: 8,
          company_tenants: 2,
          person_tenants: 8,
          tenants_with_dependents: 3,
          tenants_with_furniture: 5,
          total_dependents: 4,
          avg_dependents: 1.3,
          marital_status_distribution: [],
        },
      }),
    );

    renderWithProviders(<TenantStatisticsWidget />);

    await waitFor(() => {
      expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
    });
  });
});
