import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { FinancialSummaryWidget } from '../financial-summary-widget';
import * as dashboardHooks from '@/lib/api/hooks/use-dashboard';

type FinancialSummaryResult = ReturnType<typeof dashboardHooks.useDashboardFinancialSummary>;

function makeQueryResult(overrides: Partial<FinancialSummaryResult>): FinancialSummaryResult {
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
  } as FinancialSummaryResult;
}

describe('FinancialSummaryWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows skeleton loading state while fetching', () => {
    vi.spyOn(dashboardHooks, 'useDashboardFinancialSummary').mockReturnValue(
      makeQueryResult({ isLoading: true, isPending: true, fetchStatus: 'fetching' }),
    );

    renderWithProviders(<FinancialSummaryWidget />);

    // DashboardWidgetWrapper renders the title and skeletons during loading
    expect(screen.getByText('Resumo Financeiro')).toBeInTheDocument();
    // Data cards should not be visible yet
    expect(screen.queryByText('Receita Total')).not.toBeInTheDocument();
  });

  it('renders financial data cards when loaded', async () => {
    vi.spyOn(dashboardHooks, 'useDashboardFinancialSummary').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isPending: false,
        isSuccess: true,
        isFetched: true,
        status: 'success',
        data: {
          total_revenue: '8000.00',
          total_cleaning_fees: '300.00',
          total_tag_fees: '50.00',
          total_income: '8350.00',
          occupancy_rate: 80,
          total_apartments: 10,
          rented_apartments: 8,
          vacant_apartments: 2,
          revenue_per_apartment: '1043.75',
        },
      }),
    );

    renderWithProviders(<FinancialSummaryWidget />);

    await waitFor(() => {
      expect(screen.getByText('Receita Total')).toBeInTheDocument();
      expect(screen.getByText('Taxa de Ocupação')).toBeInTheDocument();
      expect(screen.getByText('Apartamentos Vagos')).toBeInTheDocument();
      expect(screen.getByText('Receita por Apartamento')).toBeInTheDocument();
    });
  });

  it('shows error alert when API call fails', async () => {
    vi.spyOn(dashboardHooks, 'useDashboardFinancialSummary').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isPending: false,
        isError: true,
        isLoadingError: true,
        status: 'error',
        error: new Error('Server error'),
        isFetched: true,
      }),
    );

    renderWithProviders(<FinancialSummaryWidget />);

    await waitFor(() => {
      expect(
        screen.getByText(/erro ao carregar dados/i),
      ).toBeInTheDocument();
    });
  });

  it('renders nothing when there is no data and no loading or error', () => {
    vi.spyOn(dashboardHooks, 'useDashboardFinancialSummary').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isPending: false,
        isSuccess: true,
        status: 'success',
        data: undefined,
      }),
    );

    const { container } = renderWithProviders(<FinancialSummaryWidget />);

    expect(container).toBeEmptyDOMElement();
  });

  it('displays occupancy rate with percent suffix', async () => {
    vi.spyOn(dashboardHooks, 'useDashboardFinancialSummary').mockReturnValue(
      makeQueryResult({
        isLoading: false,
        isPending: false,
        isSuccess: true,
        isFetched: true,
        status: 'success',
        data: {
          total_revenue: '5000.00',
          total_cleaning_fees: '200.00',
          total_tag_fees: '50.00',
          total_income: '5250.00',
          occupancy_rate: 75,
          total_apartments: 4,
          rented_apartments: 3,
          vacant_apartments: 1,
          revenue_per_apartment: '1750.00',
        },
      }),
    );

    renderWithProviders(<FinancialSummaryWidget />);

    await waitFor(() => {
      // The value 75 is displayed with suffix "%"
      expect(screen.getByText('75%')).toBeInTheDocument();
      // Description shows rented/total apartments
      expect(screen.getByText('3 de 4 apartamentos')).toBeInTheDocument();
    });
  });
});
