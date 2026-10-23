import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { TerminationFeeEstimate } from '../termination-fee-estimate';
import { renderWithProviders } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

describe('TerminationFeeEstimate', () => {
  it('shows the server estimate without creating a charge', async () => {
    server.use(
      http.get('*/api/leases/1/calculate_termination_fee/', () =>
        HttpResponse.json({ termination_fee_estimate: '1925.00' })
      )
    );
    renderWithProviders(<TerminationFeeEstimate leaseId={1} />);
    expect(await screen.findByText(/1.925,00/)).toBeInTheDocument();
    expect(screen.getByText(/Encerrar não gera cobrança automática/)).toBeInTheDocument();
  });

  it('shows a failed estimate without inventing a zero fee', async () => {
    server.use(
      http.get(
        '*/api/leases/1/calculate_termination_fee/',
        () => new HttpResponse(null, { status: 400 })
      )
    );
    renderWithProviders(<TerminationFeeEstimate leaseId={1} />);
    expect(await screen.findByText(/Cálculo indisponível/)).toBeInTheDocument();
  });
});
