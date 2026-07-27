import { describe, it, expect, vi, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockBill } from '@/tests/mocks/data/finances';
import { BillStatusActions } from '../bill-status-actions';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { Bill } from '@/lib/schemas/finances/bill.schema';

const API_BASE = 'http://localhost:8008/api';

/** The dropdown menu items require a menu context (Radix) to render/click reliably. */
function renderInMenu(bill: Bill) {
  return renderWithProviders(
    <DropdownMenu open>
      <DropdownMenuTrigger>Ações</DropdownMenuTrigger>
      <DropdownMenuContent>
        <BillStatusActions bill={bill} />
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

describe('BillStatusActions', () => {
  beforeEach(() => {
    vi.mocked(toast.success).mockReset();
    vi.mocked(toast.error).mockReset();
  });

  it.each([
    { action: 'suspend', label: 'Suspender' },
    { action: 'defer', label: 'Deferir' },
    { action: 'cancel', label: 'Cancelar' },
  ])(
    'shows an actionable "Abrir fechamento" toast when $action hits a closed month',
    async ({ action, label }) => {
      server.use(
        http.post(`${API_BASE}/finances/bills/:id/${action}/`, () =>
          HttpResponse.json({ detail: 'Competência 06/2026 está fechada.' }, { status: 400 })
        )
      );
      const bill = createMockBill({ id: 7, lifecycle_state: 'active' }) as unknown as Bill;

      const { queryClient } = renderInMenu(bill);
      const user = userEvent.setup({ pointerEventsCheck: 0 });
      await user.click(screen.getByText(label));

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          'Competência 06/2026 está fechada.',
          expect.objectContaining({
            action: expect.objectContaining({ label: 'Abrir fechamento' }) as unknown,
          })
        );
      });

      await waitForQueriesToSettle(queryClient);
    }
  );

  it('shows an actionable "Abrir fechamento" toast when reactivate hits a closed month', async () => {
    server.use(
      http.post(`${API_BASE}/finances/bills/:id/reactivate/`, () =>
        HttpResponse.json({ detail: 'Competência 06/2026 está fechada.' }, { status: 400 })
      )
    );
    const bill = createMockBill({ id: 7, lifecycle_state: 'suspended' }) as unknown as Bill;

    const { queryClient } = renderInMenu(bill);
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    await user.click(screen.getByText('Reativar'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        'Competência 06/2026 está fechada.',
        expect.objectContaining({
          action: expect.objectContaining({ label: 'Abrir fechamento' }) as unknown,
        })
      );
    });

    await waitForQueriesToSettle(queryClient);
  });

  it('shows a plain success toast on suspend', async () => {
    server.use(
      http.post(`${API_BASE}/finances/bills/:id/suspend/`, () =>
        HttpResponse.json(createMockBill({ id: 7, lifecycle_state: 'suspended' }))
      )
    );
    const bill = createMockBill({ id: 7, lifecycle_state: 'active' }) as unknown as Bill;

    const { queryClient } = renderInMenu(bill);
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    await user.click(screen.getByText('Suspender'));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Conta suspensa');
    });

    await waitForQueriesToSettle(queryClient);
  });
});
