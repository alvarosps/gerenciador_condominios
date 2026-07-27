import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor, fireEvent, within } from '@testing-library/react';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import MonthClosePage from '../page';
import {
  createMockCondoMonthClose,
  createMockBill,
  createMockMonthBoard,
} from '@/tests/mocks/data/finances';

const API_BASE = 'http://localhost:8008/api';

function setStaff(isStaff: boolean) {
  useAuthStore.setState({
    user: { id: 1, email: 'a@b.c', first_name: 'A', last_name: 'B', is_staff: isStaff },
    isAuthenticated: true,
  });
}

function setCloses(closes: unknown[]) {
  server.use(http.get(`${API_BASE}/finances/condo-month-closes/`, () => HttpResponse.json(closes)));
}

function spyMonthBoard() {
  const calls: { year: string | null; month: string | null }[] = [];
  server.use(
    http.get(`${API_BASE}/finances/finance-dashboard/month_board/`, ({ request }) => {
      const params = new URL(request.url).searchParams;
      calls.push({ year: params.get('year'), month: params.get('month') });
      return HttpResponse.json(
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
    })
  );
  return calls;
}

function setMonthBoardOpenBills() {
  server.use(
    http.get(`${API_BASE}/finances/finance-dashboard/month_board/`, () =>
      HttpResponse.json(
        createMockMonthBoard({
          groups: [
            {
              building_id: 1,
              building_label: 'Prédio 836',
              bills: [
                createMockBill({ id: 1, description: 'Água 836', amount_remaining: '150.00' }),
              ],
            },
          ],
          totals: { due: '150.00', paid: '0.00', remaining: '150.00', overdue: '0.00' },
        })
      )
    )
  );
}

function spyClose() {
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.post(`${API_BASE}/finances/condo-month-closes/close/`, async ({ request }) => {
      bodies.push((await request.json()) as Record<string, unknown>);
      return HttpResponse.json(
        createMockCondoMonthClose({ reference_month: '2026-05-01', status: 'closed' })
      );
    })
  );
  return bodies;
}

describe('MonthClosePage — close preflight', () => {
  it('fetches the month board for the dialog competence when the close dialog opens', async () => {
    setStaff(true);
    const calls = spyMonthBoard();
    setCloses([
      createMockCondoMonthClose({ id: 1, reference_month: '2026-05-01', status: 'open' }),
    ]);

    const { queryClient } = renderWithProviders(<MonthClosePage />);

    const [openBtn] = await screen.findAllByRole('button', { name: 'Fechar' });
    if (!openBtn) throw new Error('Fechar button not found');
    fireEvent.click(openBtn);

    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toEqual({ year: '2026', month: '5' });

    await waitForQueriesToSettle(queryClient);
  });

  it('disables "Fechar mês" until the open-bills checkbox is confirmed', async () => {
    setStaff(true);
    setMonthBoardOpenBills();
    setCloses([
      createMockCondoMonthClose({ id: 1, reference_month: '2026-05-01', status: 'open' }),
    ]);

    const { queryClient } = renderWithProviders(<MonthClosePage />);

    const [openBtn] = await screen.findAllByRole('button', { name: 'Fechar' });
    if (!openBtn) throw new Error('Fechar button not found');
    fireEvent.click(openBtn);

    const dialog = await screen.findByRole('alertdialog');
    const confirmButton = await within(dialog).findByRole('button', { name: 'Fechar mês' });
    expect(confirmButton).toBeDisabled();

    const checkbox = await within(dialog).findByRole('checkbox', {
      name: /entendo que essas contas permanecerão em aberto/i,
    });
    fireEvent.click(checkbox);

    await waitFor(() => expect(confirmButton).not.toBeDisabled());

    await waitForQueriesToSettle(queryClient);
  });

  it('closes normally (single confirm) when there are no open bills', async () => {
    setStaff(true);
    spyMonthBoard();
    const bodies = spyClose();
    setCloses([
      createMockCondoMonthClose({ id: 1, reference_month: '2026-05-01', status: 'open' }),
    ]);

    renderWithProviders(<MonthClosePage />);

    const [openBtn] = await screen.findAllByRole('button', { name: 'Fechar' });
    if (!openBtn) throw new Error('Fechar button not found');
    fireEvent.click(openBtn);

    const dialog = await screen.findByRole('alertdialog');
    const confirmButton = await within(dialog).findByRole('button', { name: 'Fechar mês' });
    await waitFor(() => expect(confirmButton).not.toBeDisabled());
    fireEvent.click(confirmButton);

    await waitFor(() => expect(bodies).toHaveLength(1));
  });

  it('keeps the reopen dialog untouched (no preflight, no checkbox)', async () => {
    setStaff(true);
    const calls = spyMonthBoard();
    setCloses([
      createMockCondoMonthClose({ id: 1, reference_month: '2026-05-01', status: 'closed' }),
    ]);

    const { queryClient } = renderWithProviders(<MonthClosePage />);

    const [reopenBtn] = await screen.findAllByRole('button', { name: 'Reabrir' });
    if (!reopenBtn) throw new Error('Reabrir button not found');
    fireEvent.click(reopenBtn);

    const dialog = await screen.findByRole('alertdialog');
    expect(within(dialog).queryByRole('checkbox')).not.toBeInTheDocument();
    const confirmButton = within(dialog).getByRole('button', { name: 'Reabrir mês' });
    expect(confirmButton).not.toBeDisabled();
    expect(calls).toHaveLength(0);

    await waitForQueriesToSettle(queryClient);
  });
});
