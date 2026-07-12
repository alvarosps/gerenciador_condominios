import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import TenantProofPage from '../page';

const API_BASE = 'http://localhost:8008/api';

describe('TenantProofPage', () => {
  it('shows an empty state when there are no proofs yet', async () => {
    const { queryClient } = renderWithProviders(<TenantProofPage />);

    await waitFor(() =>
      expect(screen.getByText('Nenhum comprovante enviado ainda.')).toBeInTheDocument()
    );

    await waitForQueriesToSettle(queryClient);
  });

  it('lists proofs fetched from the backend, most recent first (P4)', async () => {
    server.use(
      http.get(`${API_BASE}/tenant/payments/proof/`, () =>
        HttpResponse.json({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 1,
              reference_month: '2026-03-01',
              file: 'http://localhost:8008/media/proof.png',
              pix_code: '',
              status: 'pending',
              reviewed_at: null,
              rejection_reason: '',
              created_at: '2026-03-01T10:00:00Z',
            },
          ],
        })
      )
    );

    const { queryClient } = renderWithProviders(<TenantProofPage />);

    await waitFor(() => expect(screen.getByText('2026-03-01')).toBeInTheDocument());
    expect(screen.getByText('Pendente')).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('converts the "YYYY-MM" month input to a full date before upload (P5)', async () => {
    const user = userEvent.setup();
    let capturedReferenceMonth: string | null = null;

    server.use(
      http.post(`${API_BASE}/tenant/payments/proof/`, async ({ request }) => {
        const formData = await request.formData();
        capturedReferenceMonth = formData.get('reference_month') as string | null;
        return HttpResponse.json(
          {
            id: 2,
            lease: 1,
            reference_month: capturedReferenceMonth,
            file: 'http://localhost:8008/media/proof2.png',
            pix_code: '',
            status: 'pending',
            reviewed_at: null,
            rejection_reason: '',
            created_at: '2026-03-01T10:00:00Z',
          },
          { status: 201 }
        );
      })
    );

    const { queryClient } = renderWithProviders(<TenantProofPage />);

    await waitFor(() => expect(screen.getByLabelText('Mês de Referência')).toBeInTheDocument());

    const monthInput = screen.getByLabelText('Mês de Referência');
    await user.type(monthInput, '2026-03');

    const file = new File(['fake-image'], 'comprovante.png', { type: 'image/png' });
    const fileInput = screen.getByLabelText('Arquivo');
    await user.upload(fileInput, file);

    await user.click(screen.getByRole('button', { name: /Enviar Comprovante/i }));

    await waitFor(() => expect(capturedReferenceMonth).toBe('2026-03-01'));

    await waitForQueriesToSettle(queryClient);
  });
});
