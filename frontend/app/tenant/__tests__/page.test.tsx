import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import TenantDashboardPage from '../page';

const API_BASE = 'http://localhost:8008/api';

describe('TenantDashboardPage', () => {
  it('renders the rent card when the tenant has an active lease', async () => {
    const { queryClient } = renderWithProviders(<TenantDashboardPage />);

    await waitFor(() => expect(screen.getByText('Aluguel mensal')).toBeInTheDocument());

    await waitForQueriesToSettle(queryClient);
  });

  it('renders an empty-state instead of crashing when there is no active lease (P8)', async () => {
    server.use(
      http.get(`${API_BASE}/tenant/me/`, () =>
        HttpResponse.json({
          id: 2,
          name: 'Sem Locação',
          cpf_cnpj: '11144477735',
          phone: '(11) 90000-0000',
          marital_status: 'Solteiro(a)',
          profession: 'Autônomo',
          due_day: 10,
          dependents: [],
        })
      )
    );

    const { queryClient } = renderWithProviders(<TenantDashboardPage />);

    await waitFor(() => expect(screen.getByText('Nenhuma locação ativa')).toBeInTheDocument());
    expect(screen.queryByText('Aluguel mensal')).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });
});
