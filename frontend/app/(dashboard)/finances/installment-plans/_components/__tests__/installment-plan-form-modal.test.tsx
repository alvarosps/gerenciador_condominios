import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockInstallmentPlan, createMockBillingAccount } from '@/tests/mocks/data/finances';
import type { InstallmentPlan } from '@/lib/schemas/finances/installment-plan.schema';
import { installmentPlanSchema } from '@/lib/schemas/finances/installment-plan.schema';
import { InstallmentPlanFormModal } from '../installment-plan-form-modal';

const API_BASE = 'http://localhost:8008/api';

// The create/update is exercised through the real useCreate/useUpdateInstallmentPlan mutations
// hitting MSW (the HTTP boundary) — no hook is mocked. The building / category / billing-account
// selects come from the real read hooks served by the default handlers. `toast` is the global
// sonner mock from tests/setup.ts.

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
// submit-button click into a form submit) — the project's established pattern.
function submitDialogForm() {
  const formEl = screen.getByRole('dialog').querySelector('form');
  if (!formEl) throw new Error('dialog form not found');
  fireEvent.submit(formEl);
}

function spyCreate() {
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.post(`${API_BASE}/finances/installment-plans/`, async ({ request }) => {
      bodies.push((await request.json()) as Record<string, unknown>);
      return HttpResponse.json(createMockInstallmentPlan({ id: 99 }), { status: 201 });
    })
  );
  return bodies;
}

function spyUpdate(planId: number) {
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.patch(`${API_BASE}/finances/installment-plans/${planId}/`, async ({ request }) => {
      bodies.push((await request.json()) as Record<string, unknown>);
      return HttpResponse.json(createMockInstallmentPlan({ id: planId }));
    })
  );
  return bodies;
}

describe('InstallmentPlanFormModal', () => {
  beforeEach(() => {
    vi.mocked(toast.success).mockReset();
    vi.mocked(toast.error).mockReset();
  });

  it('submits a standalone plan with the write payload', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const bodies = spyCreate();
    const onClose = vi.fn();
    const { queryClient } = renderWithProviders(
      <InstallmentPlanFormModal open plan={null} onClose={onClose} />
    );

    await user.type(screen.getByLabelText('Descrição'), 'IPTU 2026');
    await user.clear(screen.getByLabelText('Valor total'));
    await user.type(screen.getByLabelText('Valor total'), '1500');
    await user.clear(screen.getByLabelText('Nº de parcelas'));
    await user.type(screen.getByLabelText('Nº de parcelas'), '3');
    await user.type(screen.getByLabelText('Primeira parcela'), '2026-07-10');

    submitDialogForm();

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({
      description: 'IPTU 2026',
      total_amount: 1500,
      installment_count: 3,
      start_due_date: '2026-07-10',
      embedded: false,
      billing_account_id: null,
      building_id: null,
      category_id: null,
      lifecycle_state: 'active',
    });
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(toast.success).toHaveBeenCalledWith('Plano de parcelas criado com sucesso');

    await waitForQueriesToSettle(queryClient);
  });

  it('reveals and requires the billing account when embedded is on', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const bodies = spyCreate();
    const { queryClient } = renderWithProviders(
      <InstallmentPlanFormModal open plan={null} onClose={vi.fn()} />
    );

    // The linked-account select is hidden while embedded is off.
    expect(screen.queryByText('Conta recorrente vinculada')).not.toBeInTheDocument();

    await user.type(screen.getByLabelText('Descrição'), 'Parcela embutida');
    await user.type(screen.getByLabelText('Primeira parcela'), '2026-07-10');
    await user.click(screen.getByLabelText('Parcela embutida'));

    // Now the field appears.
    expect(await screen.findByText('Conta recorrente vinculada')).toBeInTheDocument();

    // Submitting without a linked account is blocked by the superRefine (PT message).
    submitDialogForm();
    expect(
      await screen.findByText('Conta recorrente vinculada é obrigatória para parcela embutida')
    ).toBeInTheDocument();
    expect(bodies).toHaveLength(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('submits an embedded plan with billing_account_id once an account is chosen', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const bodies = spyCreate();
    // Deterministic single linked account so the select option is unambiguous.
    server.use(
      http.get(`${API_BASE}/finances/billing-accounts/`, () =>
        HttpResponse.json([createMockBillingAccount({ id: 8, name: 'Conta de Luz' })])
      )
    );
    const { queryClient } = renderWithProviders(
      <InstallmentPlanFormModal open plan={null} onClose={vi.fn()} />
    );

    await user.type(screen.getByLabelText('Descrição'), 'Parcela embutida');
    await user.type(screen.getByLabelText('Primeira parcela'), '2026-07-10');
    await user.click(screen.getByLabelText('Parcela embutida'));

    // Open the linked-account select and pick the account.
    await user.click(await screen.findByRole('combobox', { name: /conta recorrente vinculada/i }));
    await user.click(await screen.findByRole('option', { name: 'Conta de Luz' }));

    submitDialogForm();

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({
      description: 'Parcela embutida',
      embedded: true,
      billing_account_id: 8,
      lifecycle_state: 'active',
    });

    await waitForQueriesToSettle(queryClient);
  });

  it('blocks submission and shows a PT message when the description is empty', async () => {
    const bodies = spyCreate();
    const { queryClient } = renderWithProviders(
      <InstallmentPlanFormModal open plan={null} onClose={vi.fn()} />
    );

    submitDialogForm();
    expect(await screen.findByText('Descrição é obrigatória')).toBeInTheDocument();
    expect(bodies).toHaveLength(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('pre-fills fields on edit and PATCHes the update payload', async () => {
    const bodies = spyUpdate(1);
    const plan: InstallmentPlan = installmentPlanSchema.parse(
      createMockInstallmentPlan({
        id: 1,
        description: 'IPTU 2026',
        total_amount: '1500.00',
        installment_count: 3,
        start_due_date: '2026-07-10',
        building: null,
        category: null,
        billing_account: null,
      })
    );
    const onClose = vi.fn();
    const { queryClient } = renderWithProviders(
      <InstallmentPlanFormModal open plan={plan} onClose={onClose} />
    );

    expect(screen.getByLabelText('Descrição')).toHaveValue('IPTU 2026');
    submitDialogForm();

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({ id: 1, description: 'IPTU 2026' });
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(toast.success).toHaveBeenCalledWith('Plano de parcelas atualizado com sucesso');

    await waitForQueriesToSettle(queryClient);
  });
});
