import { describe, it, expect, vi } from 'vitest';
import { http, HttpResponse, delay } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { TenantStatisticsWidget } from '../tenant-statistics-widget';

const API_BASE = 'http://localhost:8008/api';

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  PieChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie-chart">{children}</div>
  ),
  Pie: () => null,
  Cell: () => null,
  Tooltip: () => null,
  Legend: () => null,
}));

function setTenantStatisticsResponse(data: Record<string, unknown>) {
  server.use(http.get(`${API_BASE}/dashboard/tenant_statistics/`, () => HttpResponse.json(data)));
}

describe('TenantStatisticsWidget', () => {
  it('shows loading state while fetching', async () => {
    server.use(
      http.get(`${API_BASE}/dashboard/tenant_statistics/`, async () => {
        await delay(50);
        return HttpResponse.json({});
      })
    );
    const { queryClient } = renderWithProviders(<TenantStatisticsWidget />);

    expect(screen.getByText('Estatísticas de Inquilinos')).toBeInTheDocument();
    expect(screen.queryByText('Total de Inquilinos')).not.toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('shows error state when API call fails', async () => {
    server.use(
      http.get(`${API_BASE}/dashboard/tenant_statistics/`, () =>
        HttpResponse.json({ detail: 'Server error' }, { status: 500 })
      )
    );
    const { queryClient } = renderWithProviders(<TenantStatisticsWidget />);

    await waitFor(() => {
      expect(screen.getByText(/erro ao carregar estatísticas/i)).toBeInTheDocument();
    });
    await waitForQueriesToSettle(queryClient);
  });

  it('renders statistics when loaded', async () => {
    setTenantStatisticsResponse({
      total_tenants: 20,
      individual_tenants: 15,
      company_tenants: 5,
      person_tenants: 15,
      tenants_with_dependents: 8,
      tenants_with_furniture: 10,
      total_dependents: 12,
      avg_dependents: 1.5,
      marital_status_distribution: [],
    });
    const { queryClient } = renderWithProviders(<TenantStatisticsWidget />);

    await waitFor(() => {
      expect(screen.getByText('Total de Inquilinos')).toBeInTheDocument();
      expect(screen.getByText('Com Dependentes')).toBeInTheDocument();
    });
    await waitForQueriesToSettle(queryClient);
  });

  it('displays total tenants count', async () => {
    setTenantStatisticsResponse({
      total_tenants: 25,
      individual_tenants: 20,
      company_tenants: 5,
      person_tenants: 20,
      tenants_with_dependents: 10,
      tenants_with_furniture: 12,
      total_dependents: 15,
      avg_dependents: 1.5,
      marital_status_distribution: [],
    });
    const { queryClient } = renderWithProviders(<TenantStatisticsWidget />);

    await waitFor(() => {
      expect(screen.getByText('25')).toBeInTheDocument();
    });
    await waitForQueriesToSettle(queryClient);
  });

  it('renders pie chart when data loaded', async () => {
    setTenantStatisticsResponse({
      total_tenants: 10,
      individual_tenants: 8,
      company_tenants: 2,
      person_tenants: 8,
      tenants_with_dependents: 3,
      tenants_with_furniture: 5,
      total_dependents: 4,
      avg_dependents: 1.3,
      marital_status_distribution: [],
    });
    const { queryClient } = renderWithProviders(<TenantStatisticsWidget />);

    await waitFor(() => {
      expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
    });
    await waitForQueriesToSettle(queryClient);
  });
});
