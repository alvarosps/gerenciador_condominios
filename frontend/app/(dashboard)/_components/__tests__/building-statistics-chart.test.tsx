import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { BuildingStatisticsChart } from '../building-statistics-chart';
import * as dashboardHooks from '@/lib/api/hooks/use-dashboard';

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  Cell: () => null,
}));

type BuildingStatisticsResult = ReturnType<typeof dashboardHooks.useDashboardBuildingStatistics>;

function makeQueryResult(overrides: Partial<BuildingStatisticsResult>): BuildingStatisticsResult {
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
  } as BuildingStatisticsResult;
}

const mockBuildingData = [
  {
    building_id: 1,
    building_number: '836',
    total_apartments: 10,
    rented_apartments: 8,
    vacant_apartments: 2,
    occupancy_rate: 80,
    total_revenue: '9600.00',
  },
];

describe('BuildingStatisticsChart', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows loading state while fetching', () => {
    vi.spyOn(dashboardHooks, 'useDashboardBuildingStatistics').mockReturnValue(
      makeQueryResult({ isLoading: true, isPending: true, fetchStatus: 'fetching' }),
    );

    renderWithProviders(<BuildingStatisticsChart />);

    expect(screen.getByText('Estatísticas por Prédio')).toBeInTheDocument();
    expect(screen.queryByTestId('bar-chart')).not.toBeInTheDocument();
  });

  it('shows error state when API call fails', async () => {
    vi.spyOn(dashboardHooks, 'useDashboardBuildingStatistics').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isError: true,
        status: 'error',
        error: new Error('Server error'),
      }),
    );

    renderWithProviders(<BuildingStatisticsChart />);

    await waitFor(() => {
      expect(screen.getByText(/erro ao carregar estatísticas/i)).toBeInTheDocument();
    });
  });

  it('shows empty state when no buildings', async () => {
    vi.spyOn(dashboardHooks, 'useDashboardBuildingStatistics').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isSuccess: true,
        isFetched: true,
        status: 'success',
        data: [],
      }),
    );

    renderWithProviders(<BuildingStatisticsChart />);

    await waitFor(() => {
      expect(screen.getByText(/nenhum prédio cadastrado/i)).toBeInTheDocument();
    });
  });

  it('renders chart with data when loaded', async () => {
    vi.spyOn(dashboardHooks, 'useDashboardBuildingStatistics').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isSuccess: true,
        isFetched: true,
        status: 'success',
        data: mockBuildingData,
      }),
    );

    renderWithProviders(<BuildingStatisticsChart />);

    await waitFor(() => {
      expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
    });
  });

  it('shows summary statistics', async () => {
    vi.spyOn(dashboardHooks, 'useDashboardBuildingStatistics').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isSuccess: true,
        isFetched: true,
        status: 'success',
        data: mockBuildingData,
      }),
    );

    renderWithProviders(<BuildingStatisticsChart />);

    await waitFor(() => {
      expect(screen.getByText('Prédios')).toBeInTheDocument();
      expect(screen.getByText('Total Aptos')).toBeInTheDocument();
      expect(screen.getByText('Aptos Alugados')).toBeInTheDocument();
      expect(screen.getByText('Receita Total')).toBeInTheDocument();
    });
  });
});
