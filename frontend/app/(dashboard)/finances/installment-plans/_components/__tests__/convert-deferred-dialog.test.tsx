import { describe, it, expect, vi, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { toast } from 'sonner';
import { renderWithProviders } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockInstallmentPlan } from '@/tests/mocks/data/finances';
import { ConvertDeferredDialog } from '../convert-deferred-dialog';

const API_BASE = 'http://localhost:8008/api';

// The conversion is exercised through the real useConvertDeferred mutation hitting MSW (the HTTP
// boundary) — no hook is mocked. `toast` is the global sonner mock from tests/setup.ts.

// Radix Dialog forms must be submitted via the form element (happy-dom does not translate a
// submit-button click into a form submit) — the project's established pattern.
function submitDialogForm() {
  const formEl = screen.getByRole('dialog').querySelector('form');
  if (!formEl) throw new Error('dialog form not found');
  fireEvent.submit(formEl);
}

function spyConvert() {
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.post(`${API_BASE}/finances/installment-plans/convert_deferred/`, async ({ request }) => {
      bodies.push((await request.json()) as Record<string, unknown>);
      return HttpResponse.json(createMockInstallmentPlan({ id: 2 }), { status: 201 });
    })
  );
  return bodies;
}

describe('ConvertDeferredDialog', () => {
  beforeEach(() => {
    vi.mocked(toast.success).mockReset();
    vi.mocked(toast.error).mockReset();
  });

  it('shows the "valor preservado" note (the FE never sums the total)', () => {
    renderWithProviders(
      <ConvertDeferredDialog open billId={42} description="IPTU 2026" onClose={vi.fn()} />
    );
    expect(screen.getByText(/o valor total é preservado/i)).toBeInTheDocument();
  });

  it('submits convert with bill_id + params and toasts on success', async () => {
    const bodies = spyConvert();
    const onClose = vi.fn();

    renderWithProviders(
      <ConvertDeferredDialog open billId={42} description="IPTU 2026" onClose={onClose} />
    );

    submitDialogForm();

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({
      bill_id: 42,
      installment_count: 3,
      default_due_day: 10,
    });
    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith('Plano de parcelas criado a partir do item adiado')
    );
    expect(onClose).toHaveBeenCalled();
  });

  it('keeps the dialog open and logs the PT error on a 400 rejection', async () => {
    // The convert flow routes failures through handleError (console.error), not a toast — so the
    // observable error behavior is: success toast NOT fired and the dialog stays open (no onClose).
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    server.use(
      http.post(`${API_BASE}/finances/installment-plans/convert_deferred/`, () =>
        HttpResponse.json({ error: 'Item não está adiado.' }, { status: 400 })
      )
    );
    const onClose = vi.fn();
    renderWithProviders(
      <ConvertDeferredDialog open billId={42} description="IPTU 2026" onClose={onClose} />
    );

    submitDialogForm();

    await waitFor(() =>
      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('Item não está adiado.'),
        expect.anything()
      )
    );
    expect(toast.success).not.toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();
    errorSpy.mockRestore();
  });

  it('does not submit when billId is null', async () => {
    const bodies = spyConvert();
    renderWithProviders(
      <ConvertDeferredDialog open billId={null} description="IPTU 2026" onClose={vi.fn()} />
    );

    submitDialogForm();

    // Give any (unexpected) request a chance to land before asserting nothing was posted.
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(bodies).toHaveLength(0);
  });
});
