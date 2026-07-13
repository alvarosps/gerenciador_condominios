import { describe, it, expect, vi } from 'vitest';
import { http, HttpResponse, delay } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { BuildingStatisticsChart } from '../building-statistics-chart';

const API_BASE = 'http://localhost:8008/api';

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  Cell: () => null,
}));

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

function setBuildingStatisticsResponse(data: typeof mockBuildingData) {
  server.use(http.get(`${API_BASE}/dashboard/building_statistics/`, () => HttpResponse.json(data)));
}

describe('BuildingStatisticsChart', () => {
  it('shows loading state while fetching', async () => {
    server.use(
      http.get(`${API_BASE}/dashboard/building_statistics/`, async () => {
        await delay(50);
        return HttpResponse.json(mockBuildingData);
      })
    );
    const { queryClient } = renderWithProviders(<BuildingStatisticsChart />);

    expect(screen.getByText('Estatísticas por Prédio')).toBeInTheDocument();
    expect(screen.queryByTestId('bar-chart')).not.toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('shows error state when API call fails', async () => {
    server.use(
      http.get(`${API_BASE}/dashboard/building_statistics/`, () =>
        HttpResponse.json({ detail: 'Server error' }, { status: 500 })
      )
    );
    const { queryClient } = renderWithProviders(<BuildingStatisticsChart />);

    await waitFor(() => {
      expect(screen.getByText(/erro ao carregar estatísticas/i)).toBeInTheDocument();
    });
    await waitForQueriesToSettle(queryClient);
  });

  it('shows empty state when no buildings', async () => {
    setBuildingStatisticsResponse([]);
    const { queryClient } = renderWithProviders(<BuildingStatisticsChart />);

    await waitFor(() => {
      expect(screen.getByText(/nenhum prédio cadastrado/i)).toBeInTheDocument();
    });
    await waitForQueriesToSettle(queryClient);
  });

  it('renders chart with data when loaded', async () => {
    setBuildingStatisticsResponse(mockBuildingData);
    const { queryClient } = renderWithProviders(<BuildingStatisticsChart />);

    await waitFor(() => {
      expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
    });
    await waitForQueriesToSettle(queryClient);
  });

  it('shows summary statistics', async () => {
    setBuildingStatisticsResponse(mockBuildingData);
    const { queryClient } = renderWithProviders(<BuildingStatisticsChart />);

    await waitFor(() => {
      expect(screen.getByText('Prédios')).toBeInTheDocument();
      expect(screen.getByText('Total Aptos')).toBeInTheDocument();
      expect(screen.getByText('Aptos Alugados')).toBeInTheDocument();
      expect(screen.getByText('Receita Total')).toBeInTheDocument();
    });
    await waitForQueriesToSettle(queryClient);
  });
});
