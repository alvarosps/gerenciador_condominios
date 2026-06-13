import { describe, it, expect, vi, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { WithdrawDialog } from '../_components/withdraw-dialog';
import { createMockReserve } from '@/tests/mocks/data/finances';
import { reserveSchema } from '@/lib/schemas/finances/reserve.schema';
import { toast } from 'sonner';

const API_BASE = 'http://localhost:8008/api';

// The withdraw goes through the real useWithdrawReserve mutation hitting MSW — no hook is mocked.
// `toast` is the global sonner mock from tests/setup.ts.
function reserve(id = 5, balance = '1000.00') {
  return reserveSchema.parse(createMockReserve({ id, balance }));
}

function submitDialogForm() {
  const formEl = screen.getByRole('dialog').querySelector('form');
  if (!formEl) throw new Error('dialog form not found');
  fireEvent.submit(formEl);
}

function spyWithdraw(reserveId: number) {
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.post(`${API_BASE}/finances/reserves/${reserveId}/withdraw/`, async ({ request }) => {
      bodies.push((await request.json()) as Record<string, unknown>);
      return HttpResponse.json(createMockReserve({ id: reserveId, balance: '700.00' }));
    })
  );
  return bodies;
}

describe('WithdrawDialog', () => {
  beforeEach(() => {
    vi.mocked(toast.success).mockReset();
    vi.mocked(toast.error).mockReset();
  });

  it('posts the withdraw to /reserves/:id/withdraw/ with the amount, then closes', async () => {
    const bodies = spyWithdraw(5);
    const onClose = vi.fn();
    renderWithProviders(<WithdrawDialog open reserve={reserve(5)} onClose={onClose} />);

    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '300' } });
    submitDialogForm();

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({ amount: 300 });
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(toast.success).toHaveBeenCalled();
  });

  it('blocks submission when amount <= 0 (Zod, PT) — nothing is posted', async () => {
    const bodies = spyWithdraw(5);
    renderWithProviders(<WithdrawDialog open reserve={reserve(5)} onClose={vi.fn()} />);

    submitDialogForm();

    expect(await screen.findByText(/maior que zero/i)).toBeInTheDocument();
    expect(bodies).toHaveLength(0);
  });

  it('shows the backend insufficient-balance PT error — the front never simulates the balance', async () => {
    server.use(
      http.post(`${API_BASE}/finances/reserves/5/withdraw/`, () =>
        HttpResponse.json({ error: 'Saldo da reserva insuficiente.' }, { status: 400 })
      )
    );
    renderWithProviders(<WithdrawDialog open reserve={reserve(5, '100.00')} onClose={vi.fn()} />);

    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '999' } });
    submitDialogForm();

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Saldo da reserva insuficiente.'));
  });
});
