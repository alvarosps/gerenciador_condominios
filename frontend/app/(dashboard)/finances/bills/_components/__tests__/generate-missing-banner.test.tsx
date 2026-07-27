import { describe, it, expect } from 'vitest';
import { http, HttpResponse, delay } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { GenerateMissingBanner } from '../generate-missing-banner';

const API_BASE = 'http://localhost:8008/api';

describe('GenerateMissingBanner', () => {
  it('renders null when missingCount is 0', () => {
    const { container } = renderWithProviders(
      <GenerateMissingBanner missingCount={0} year={2026} month={7} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('renders the count in the message and button label', async () => {
    const { queryClient } = renderWithProviders(
      <GenerateMissingBanner missingCount={3} year={2026} month={7} />
    );

    expect(
      screen.getByText(/Há 3 conta\(s\) recorrente\(s\) sem fatura gerada/)
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Gerar contas faltantes (3)' })).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('disables the button while the mutation is pending', async () => {
    server.use(
      http.post(`${API_BASE}/finances/bills/generate_month/`, async () => {
        await delay(100);
        return HttpResponse.json({ created: 3, bills: [] });
      })
    );

    const { queryClient } = renderWithProviders(
      <GenerateMissingBanner missingCount={3} year={2026} month={7} />
    );

    const button = screen.getByRole('button', { name: 'Gerar contas faltantes (3)' });
    await userEvent.click(button);

    await waitFor(() => expect(button).toBeDisabled());

    await waitForQueriesToSettle(queryClient);
  });
});
