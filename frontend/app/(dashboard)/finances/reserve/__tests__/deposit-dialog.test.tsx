import { describe, it, expect, vi, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { DepositDialog } from '../_components/deposit-dialog';
import { createMockReserve } from '@/tests/mocks/data/finances';
import { reserveSchema } from '@/lib/schemas/finances/reserve.schema';
import { toast } from 'sonner';

const API_BASE = 'http://localhost:8008/api';

// The deposit is exercised through the real useDepositReserve mutation hitting MSW (the HTTP
// boundary) — no hook is mocked. `toast` is the global sonner mock from tests/setup.ts.
function reserve(id = 3) {
  return reserveSchema.parse(createMockReserve({ id }));
}

// Radix Dialog forms must be submitted via the form element (happy-dom does not translate a
// submit-button click into a form submit) — the project's established pattern.
function submitDialogForm() {
  const formEl = screen.getByRole('dialog').querySelector('form');
  if (!formEl) throw new Error('dialog form not found');
  fireEvent.submit(formEl);
}

function spyDeposit(reserveId: number) {
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.post(`${API_BASE}/finances/reserves/${reserveId}/deposit/`, async ({ request }) => {
      bodies.push((await request.json()) as Record<string, unknown>);
      return HttpResponse.json(createMockReserve({ id: reserveId, balance: '5250.00' }));
    })
  );
  return bodies;
}

describe('DepositDialog', () => {
  beforeEach(() => {
    vi.mocked(toast.success).mockReset();
    vi.mocked(toast.error).mockReset();
  });

  it('posts the deposit to /reserves/:id/deposit/ with the amount, then closes', async () => {
    const bodies = spyDeposit(3);
    const onClose = vi.fn();
    renderWithProviders(<DepositDialog open reserve={reserve(3)} onClose={onClose} />);

    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '250' } });
    submitDialogForm();

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({ amount: 250 });
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(toast.success).toHaveBeenCalled();
  });

  it('blocks submission when amount <= 0 (Zod, PT) — nothing is posted', async () => {
    const bodies = spyDeposit(3);
    renderWithProviders(<DepositDialog open reserve={reserve(3)} onClose={vi.fn()} />);

    submitDialogForm();

    expect(await screen.findByText(/maior que zero/i)).toBeInTheDocument();
    expect(bodies).toHaveLength(0);
  });

  it('shows the server PT error on a 400 rejection (does not simulate balance)', async () => {
    server.use(
      http.post(`${API_BASE}/finances/reserves/3/deposit/`, () =>
        HttpResponse.json({ error: 'Erro do servidor.' }, { status: 400 })
      )
    );
    renderWithProviders(<DepositDialog open reserve={reserve(3)} onClose={vi.fn()} />);

    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '50' } });
    submitDialogForm();

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Erro do servidor.'));
  });
});
