import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import TenantProfilePage from '../page';

const API_BASE = 'http://localhost:8008/api';

describe('TenantProfilePage', () => {
  it('renders apartment info when the tenant has an active lease', async () => {
    const { queryClient } = renderWithProviders(<TenantProfilePage />);

    await waitFor(() => expect(screen.getByText('101')).toBeInTheDocument());

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

    const { queryClient } = renderWithProviders(<TenantProfilePage />);

    await waitFor(() => expect(screen.getByText('Nenhuma locação ativa')).toBeInTheDocument());

    await waitForQueriesToSettle(queryClient);
  });

  it('allows editing the phone (P10)', async () => {
    const user = userEvent.setup();
    server.use(
      http.patch(`${API_BASE}/auth/me/update/`, () =>
        HttpResponse.json({
          id: 10,
          email: '',
          first_name: 'João',
          last_name: 'Silva',
          is_staff: false,
        })
      )
    );

    const { queryClient } = renderWithProviders(<TenantProfilePage />);

    await waitFor(() => expect(screen.getByText('(11) 99999-0001')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Editar telefone/i }));
    const input = screen.getByPlaceholderText('(00) 00000-0000');
    await user.clear(input);
    await user.type(input, '(11) 98888-7777');
    await user.click(screen.getByRole('button', { name: /Salvar/i }));

    await waitFor(() =>
      expect(screen.queryByRole('button', { name: /Salvar/i })).not.toBeInTheDocument()
    );

    await waitForQueriesToSettle(queryClient);
  });
});
