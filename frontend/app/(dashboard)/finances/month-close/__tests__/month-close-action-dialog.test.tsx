import { describe, it, expect, vi, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { MonthCloseActionDialog } from '../_components/month-close-action-dialog';
import { createMockCondoMonthClose, createMockMonthBoard } from '@/tests/mocks/data/finances';
import { condoMonthCloseSchema } from '@/lib/schemas/finances/condo-month-close.schema';

const API_BASE = 'http://localhost:8008/api';

// The dialog takes an onConfirm/onCancel callback pair (no hook) — it owns no mutation. The raw
// mock is parsed to the typed CondoMonthClose the prop expects (money strings → numbers).
function close(overrides: Parameters<typeof createMockCondoMonthClose>[0] = {}) {
  return condoMonthCloseSchema.parse(createMockCondoMonthClose(overrides));
}

/** No open bills — the close preflight self-confirms immediately (S76 contract). */
function setMonthBoardNoOpenBills() {
  server.use(
    http.get(`${API_BASE}/finances/finance-dashboard/month_board/`, () =>
      HttpResponse.json(
        createMockMonthBoard({
          groups: [],
          totals: { due: '0.00', paid: '0.00', remaining: '0.00', overdue: '0.00' },
        })
      )
    )
  );
}

describe('MonthCloseActionDialog', () => {
  beforeEach(() => {
    setMonthBoardNoOpenBills();
  });

  const may = close({ reference_month: '2026-05-01', status: 'open' });

  it('renders the close title with the competência via formatMonthYear and confirms', async () => {
    const onConfirm = vi.fn();
    const { queryClient } = renderWithProviders(
      <MonthCloseActionDialog
        open
        close={may}
        action="close"
        year={2026}
        month={5}
        isPending={false}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />
    );
    expect(screen.getByText(/Fechar mês: Maio de 2026/)).toBeInTheDocument();

    const confirmButton = screen.getByRole('button', { name: 'Fechar mês' });
    await waitFor(() => expect(confirmButton).not.toBeDisabled());
    fireEvent.click(confirmButton);
    expect(onConfirm).toHaveBeenCalledTimes(1);

    await waitForQueriesToSettle(queryClient);
  });

  it('renders the reopen title and confirms in reopen mode', () => {
    const onConfirm = vi.fn();
    renderWithProviders(
      <MonthCloseActionDialog
        open
        close={close({ reference_month: '2026-05-01', status: 'closed' })}
        action="reopen"
        year={2026}
        month={5}
        isPending={false}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />
    );
    expect(screen.getByText(/Reabrir mês: Maio de 2026/)).toBeInTheDocument();
    // Reopen mode never renders the preflight — the confirm button is enabled immediately.
    fireEvent.click(screen.getByRole('button', { name: 'Reabrir mês' }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('disables the actions while pending (no double submit)', () => {
    renderWithProviders(
      <MonthCloseActionDialog
        open
        close={may}
        action="close"
        year={2026}
        month={5}
        isPending
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(screen.getByRole('button', { name: 'Aguarde...' })).toBeDisabled();
  });
});
