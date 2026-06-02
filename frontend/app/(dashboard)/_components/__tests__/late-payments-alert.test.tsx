import { describe, it, expect } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse, delay } from 'msw';
import { renderWithProviders, createTestQueryClient } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { LatePaymentsAlert } from '../late-payments-alert';

const API_BASE = 'http://localhost:8008/api';

const lateSummary = {
  total_late_leases: 1,
  total_late_fees: '250.00',
  average_late_days: 10,
  late_leases: [
    {
      lease_id: 1,
      apartment_number: 101,
      building_number: '836',
      tenant_name: 'João Silva',
      rental_value: '1200.00',
      due_day: 5,
      late_days: 10,
      late_months: 2,
      late_fee: '250.00',
      last_payment_date: '2026-03-05',
    },
  ],
};

describe('LatePaymentsAlert', () => {
  it('renders the late leases returned by the API (informational, no inline toggle)', async () => {
    server.use(
      http.get(`${API_BASE}/dashboard/late_payment_summary/`, () => HttpResponse.json(lateSummary)),
    );
    renderWithProviders(<LatePaymentsAlert />, { queryClient: createTestQueryClient() });

    await waitFor(() => {
      expect(screen.getByText('Pagamentos em Atraso')).toBeInTheDocument();
    });

    // Expand the accordion to reveal the late-lease details.
    await userEvent.click(screen.getByRole('button', { name: /pagamentos em atraso/i }));

    expect(await screen.findByText('João Silva')).toBeInTheDocument();
    expect(screen.getByText(/10 dias de atraso/i)).toBeInTheDocument();
    // Per-month payment is done in the rent calendar — there is no inline "Pago" toggle here.
    expect(screen.queryByRole('button', { name: /^pago$/i })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: /ver locação/i })).toBeInTheDocument();
  });

  it('shows the success state when there are no late payments', async () => {
    server.use(
      http.get(`${API_BASE}/dashboard/late_payment_summary/`, () =>
        HttpResponse.json({
          total_late_leases: 0,
          total_late_fees: '0.00',
          average_late_days: 0,
          late_leases: [],
        }),
      ),
    );
    renderWithProviders(<LatePaymentsAlert />, { queryClient: createTestQueryClient() });

    await waitFor(() => {
      expect(screen.getByText(/não há pagamentos em atraso/i)).toBeInTheDocument();
    });
  });

  it('renders nothing while loading', () => {
    server.use(
      http.get(`${API_BASE}/dashboard/late_payment_summary/`, async () => {
        await delay(100);
        return HttpResponse.json(lateSummary);
      }),
    );
    const { container } = renderWithProviders(<LatePaymentsAlert />, {
      queryClient: createTestQueryClient(),
    });
    expect(container).toBeEmptyDOMElement();
  });
});
