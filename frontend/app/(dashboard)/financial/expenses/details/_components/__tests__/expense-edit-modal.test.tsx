import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockExpense } from '@/tests/mocks/data/expenses';
import type { ExpenseDetailItem } from '@/lib/api/hooks/use-financial-dashboard';
import { ExpenseEditModal } from '../expense-edit-modal';

const API_BASE = 'http://localhost:8008/api';

// The save flow (create/rebuild) is exercised through the real apiClient hitting MSW (the HTTP
// boundary) — no internal method is mocked. `toast` is the global sonner mock from tests/setup.ts.

// Radix Select uses Pointer Capture + scrollIntoView, which happy-dom lacks — polyfill them.
beforeAll(() => {
  if (!Element.prototype.hasPointerCapture) {
    Element.prototype.hasPointerCapture = () => false;
    Element.prototype.setPointerCapture = () => undefined;
    Element.prototype.releasePointerCapture = () => undefined;
  }
  if (!Element.prototype.scrollIntoView) {
    Element.prototype.scrollIntoView = () => undefined;
  }
});

// Radix Dialog forms must be submitted via the form element (happy-dom does not translate a
// submit-button click into a form submit) — the project's established pattern. The confirm step
// is a separate AlertDialog (role="alertdialog"), clicked directly.
function submitDialogForm() {
  const formEl = screen.getByRole('dialog').querySelector('form');
  if (!formEl) throw new Error('dialog form not found');
  fireEvent.submit(formEl);
}

async function confirmSave(user: ReturnType<typeof userEvent.setup>) {
  const alertDialog = await screen.findByRole('alertdialog');
  await user.click(within(alertDialog).getByRole('button', { name: /confirmar/i }));
}

function spyCreate() {
  const bodies: Record<string, unknown>[] = [];
  const requests: unknown[] = [];
  server.use(
    http.post(`${API_BASE}/expenses/`, async ({ request }) => {
      requests.push(request);
      const body = (await request.json()) as Record<string, unknown>;
      bodies.push(body);
      return HttpResponse.json(createMockExpense({ id: 99, ...body }), { status: 201 });
    })
  );
  return { bodies, requests };
}

function spyRebuild(expenseId: number) {
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.post(`${API_BASE}/expenses/${String(expenseId)}/rebuild/`, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      bodies.push(body);
      return HttpResponse.json(createMockExpense({ id: expenseId, ...body }));
    })
  );
  return bodies;
}

describe('ExpenseEditModal', () => {
  beforeEach(() => {
    vi.mocked(toast.success).mockReset();
    vi.mocked(toast.error).mockReset();
  });

  it('F2: sends a single POST /expenses/ with installments embedded in installments_data', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const { bodies, requests } = spyCreate();
    const onSaved = vi.fn();
    const onClose = vi.fn();
    const { queryClient } = renderWithProviders(
      <ExpenseEditModal mode="create" personId={1} onClose={onClose} onSaved={onSaved} />
    );

    // Pick expense_type = personal_loan (in INSTALLMENT_TYPES, no credit-card select required).
    await user.click(screen.getByRole('combobox', { name: /tipo de despesa/i }));
    await user.click(await screen.findByRole('option', { name: 'Empréstimo Pessoal' }));

    await user.type(screen.getByLabelText('Descrição'), 'Empréstimo parcelado');
    await user.clear(screen.getByPlaceholderText('0.00'));
    await user.type(screen.getByPlaceholderText('0.00'), '150');

    await user.click(screen.getByLabelText('Parcelado'));
    await user.clear(screen.getByLabelText('Parcela Atual'));
    await user.type(screen.getByLabelText('Parcela Atual'), '1');
    await user.clear(screen.getByLabelText('Total de Parcelas'));
    await user.type(screen.getByLabelText('Total de Parcelas'), '2');

    submitDialogForm();
    await confirmSave(user);

    await waitFor(() => expect(bodies).toHaveLength(1));

    // Exactly one HTTP request reaches the server — no separate /expense-installments/ calls.
    expect(requests).toHaveLength(1);

    const body = bodies[0];
    expect(body).toMatchObject({
      description: 'Empréstimo parcelado',
      is_installment: true,
      total_installments: 2,
    });
    expect(body?.installments_data).toEqual([
      expect.objectContaining({ installment_number: 1, total_installments: 2, amount: 150 }),
      expect.objectContaining({ installment_number: 2, total_installments: 2, amount: 150 }),
    ]);

    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(toast.success).toHaveBeenCalledWith('Despesa criada com sucesso');

    await waitForQueriesToSettle(queryClient);
  });

  it('F1: clamps installment due dates across a short month instead of drifting', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const { bodies } = spyCreate();
    const { queryClient } = renderWithProviders(
      <ExpenseEditModal
        mode="create"
        personId={1}
        defaultExpenseDate="2026-01-31"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />
    );

    await user.click(screen.getByRole('combobox', { name: /tipo de despesa/i }));
    await user.click(await screen.findByRole('option', { name: 'Empréstimo Pessoal' }));

    await user.type(screen.getByLabelText('Descrição'), 'Compra dia 31');
    await user.clear(screen.getByPlaceholderText('0.00'));
    await user.type(screen.getByPlaceholderText('0.00'), '100');

    await user.click(screen.getByLabelText('Parcelado'));
    await user.clear(screen.getByLabelText('Parcela Atual'));
    await user.type(screen.getByLabelText('Parcela Atual'), '1');
    await user.clear(screen.getByLabelText('Total de Parcelas'));
    await user.type(screen.getByLabelText('Total de Parcelas'), '3');

    submitDialogForm();
    await confirmSave(user);

    await waitFor(() => expect(bodies).toHaveLength(1));
    const installments = bodies[0]?.installments_data as { due_date: string }[];
    // 31/jan -> 28/fev (clamped, 2026 is not a leap year) -> 31/mar (not carried over from Feb).
    expect(installments.map((i) => i.due_date)).toEqual(['2026-01-31', '2026-02-28', '2026-03-31']);

    await waitForQueriesToSettle(queryClient);
  });

  it('edit mode still rebuilds installments via a single POST /expenses/:id/rebuild/', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const bodies = spyRebuild(42);
    const item: ExpenseDetailItem = {
      expense_id: 42,
      installment_id: 7,
      description: 'Compra parcelada',
      installment_number: 1,
      total_installments: 2,
      amount: 150,
      due_date: '2026-01-31',
      is_paid: false,
    };
    const { queryClient } = renderWithProviders(
      <ExpenseEditModal mode="edit" item={item} personId={1} onClose={vi.fn()} onSaved={vi.fn()} />
    );

    submitDialogForm();
    await confirmSave(user);

    await waitFor(() => expect(bodies).toHaveLength(1));
    const installments = bodies[0]?.installments as { due_date: string }[];
    expect(installments.map((i) => i.due_date)).toEqual(['2026-01-31', '2026-02-28']);
    expect(toast.success).toHaveBeenCalledWith('Despesa atualizada com sucesso');

    await waitForQueriesToSettle(queryClient);
  });
});
