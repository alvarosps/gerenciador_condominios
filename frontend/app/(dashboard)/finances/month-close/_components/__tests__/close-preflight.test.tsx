import { describe, it, expect, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockBill, createMockMonthBoard } from '@/tests/mocks/data/finances';
import { ClosePreflight } from '../close-preflight';

const API_BASE = 'http://localhost:8008/api';

function setMonthBoard(board: ReturnType<typeof createMockMonthBoard>) {
  server.use(
    http.get(`${API_BASE}/finances/finance-dashboard/month_board/`, () => HttpResponse.json(board))
  );
}

describe('ClosePreflight', () => {
  it('reports confirmation=true immediately when the competence has no open bills', async () => {
    setMonthBoard(
      createMockMonthBoard({
        groups: [
          {
            building_id: 1,
            building_label: 'Prédio 836',
            bills: [createMockBill({ id: 1, amount_remaining: '0.00', payment_status: 'paid' })],
          },
        ],
        totals: { due: '350.00', paid: '350.00', remaining: '0.00', overdue: '0.00' },
      })
    );
    const onConfirmationChange = vi.fn();

    const { queryClient } = renderWithProviders(
      <ClosePreflight year={2026} month={6} onConfirmationChange={onConfirmationChange} />
    );

    await waitFor(() => expect(onConfirmationChange).toHaveBeenCalledWith(true));
    expect(await screen.findByText(/nenhuma conta em aberto/i)).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('lists count and totals.remaining verbatim when there are open bills', async () => {
    setMonthBoard(
      createMockMonthBoard({
        groups: [
          {
            building_id: 1,
            building_label: 'Prédio 836',
            bills: [
              createMockBill({ id: 1, description: 'Água 836', amount_remaining: '150.00' }),
              createMockBill({ id: 2, description: 'Luz 836', amount_remaining: '200.00' }),
              createMockBill({
                id: 3,
                description: 'Taxa quitada',
                amount_remaining: '0.00',
                payment_status: 'paid',
              }),
            ],
          },
        ],
        totals: { due: '350.00', paid: '0.00', remaining: '350.00', overdue: '0.00' },
      })
    );
    const onConfirmationChange = vi.fn();

    const { queryClient } = renderWithProviders(
      <ClosePreflight year={2026} month={6} onConfirmationChange={onConfirmationChange} />
    );

    // totals.remaining is used VERBATIM ('350.00' from the payload), never re-summed client-side.
    expect(await screen.findByText(/2 conta\(s\) em aberto/i)).toBeInTheDocument();
    expect(screen.getByText('R$ 350,00')).toBeInTheDocument();
    expect(screen.getByText(/Água 836/)).toBeInTheDocument();
    expect(screen.getByText(/Luz 836/)).toBeInTheDocument();
    expect(screen.queryByText(/Taxa quitada/)).not.toBeInTheDocument();
    // Not confirmed until the checkbox is checked.
    expect(onConfirmationChange).toHaveBeenCalledWith(false);

    await waitForQueriesToSettle(queryClient);
  });

  it('only reports confirmation=true after the explicit checkbox is checked', async () => {
    setMonthBoard(
      createMockMonthBoard({
        groups: [
          {
            building_id: 1,
            building_label: 'Prédio 836',
            bills: [createMockBill({ id: 1, amount_remaining: '150.00' })],
          },
        ],
        totals: { due: '150.00', paid: '0.00', remaining: '150.00', overdue: '0.00' },
      })
    );
    const onConfirmationChange = vi.fn();

    const { queryClient } = renderWithProviders(
      <ClosePreflight year={2026} month={6} onConfirmationChange={onConfirmationChange} />
    );

    const checkbox = await screen.findByRole('checkbox', {
      name: /entendo que essas contas permanecerão em aberto/i,
    });
    expect(onConfirmationChange).toHaveBeenLastCalledWith(false);

    await userEvent.click(checkbox);
    expect(onConfirmationChange).toHaveBeenLastCalledWith(true);

    await userEvent.click(checkbox);
    expect(onConfirmationChange).toHaveBeenLastCalledWith(false);

    await waitForQueriesToSettle(queryClient);
  });

  it('does not block closing when the board request fails (informative preflight)', async () => {
    server.use(
      http.get(`${API_BASE}/finances/finance-dashboard/month_board/`, () =>
        HttpResponse.json({ detail: 'Erro interno' }, { status: 500 })
      )
    );
    const onConfirmationChange = vi.fn();

    renderWithProviders(
      <ClosePreflight year={2026} month={6} onConfirmationChange={onConfirmationChange} />
    );

    await waitFor(() => expect(onConfirmationChange).toHaveBeenCalledWith(true));
    expect(
      await screen.findByText(/não foi possível verificar as contas em aberto/i)
    ).toBeInTheDocument();
  });
});
