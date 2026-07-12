import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import TenantContractPage from '../page';

const API_BASE = 'http://localhost:8008/api';

describe('TenantContractPage', () => {
  beforeEach(() => {
    URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows the download card when the contract has been generated', async () => {
    const { queryClient } = renderWithProviders(<TenantContractPage />);

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Baixar Contrato/i })).toBeInTheDocument()
    );

    await waitForQueriesToSettle(queryClient);
  });

  it('shows an empty-state instead of a fake card when the contract has not been generated (P11)', async () => {
    server.use(
      http.get(`${API_BASE}/tenant/me/`, () =>
        HttpResponse.json({
          id: 1,
          name: 'João Silva',
          cpf_cnpj: '12345678901',
          phone: '(11) 99999-0001',
          marital_status: 'Solteiro(a)',
          profession: 'Engenheiro',
          due_day: 5,
          dependents: [],
          lease: {
            id: 1,
            start_date: '2024-01-01',
            validity_months: 12,
            rental_value: '1300.00',
            pending_rental_value: null,
            pending_rental_value_date: null,
            number_of_tenants: 1,
            contract_generated: false,
          },
          apartment: {
            id: 1,
            number: '101',
            building_name: '836',
            building_address: 'Rua das Flores, 836',
          },
        })
      )
    );

    const { queryClient } = renderWithProviders(<TenantContractPage />);

    await waitFor(() =>
      expect(screen.getByText('Contrato ainda não foi gerado')).toBeInTheDocument()
    );
    expect(screen.queryByRole('button', { name: /Baixar Contrato/i })).not.toBeInTheDocument();
    expect(screen.queryByText('contrato.pdf')).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('shows the real backend error message on a failed download (P11)', async () => {
    const user = userEvent.setup();
    server.use(
      http.get(`${API_BASE}/tenant/contract/`, () =>
        HttpResponse.json({ detail: 'Arquivo do contrato não encontrado.' }, { status: 404 })
      )
    );

    const { queryClient } = renderWithProviders(<TenantContractPage />);

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Baixar Contrato/i })).toBeInTheDocument()
    );
    await user.click(screen.getByRole('button', { name: /Baixar Contrato/i }));

    const { toast } = await import('sonner');
    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('Arquivo do contrato não encontrado.')
    );

    await waitForQueriesToSettle(queryClient);
  });
});
