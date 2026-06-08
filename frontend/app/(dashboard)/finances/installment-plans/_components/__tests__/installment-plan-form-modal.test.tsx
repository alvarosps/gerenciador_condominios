import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/tests/test-utils';
import type { InstallmentPlan } from '@/lib/schemas/finances/installment-plan.schema';
import { InstallmentPlanFormModal } from '../installment-plan-form-modal';

const createMutate = vi.fn();
const updateMutate = vi.fn();

vi.mock('@/lib/api/hooks/use-installment-plans', () => ({
  useCreateInstallmentPlan: () => ({ mutate: createMutate, isPending: false }),
  useUpdateInstallmentPlan: () => ({ mutate: updateMutate, isPending: false }),
}));

vi.mock('@/lib/api/hooks/use-buildings', () => ({
  useBuildings: () => ({ data: [{ id: 4, name: 'Prédio 836' }] }),
}));

vi.mock('@/lib/api/hooks/use-finance-categories', () => ({
  useFinanceCategories: () => ({ data: [{ id: 5, name: 'Impostos' }] }),
}));

vi.mock('@/lib/api/hooks/use-billing-accounts', () => ({
  useBillingAccounts: () => ({ data: [{ id: 8, name: 'Conta de Luz' }] }),
}));

beforeEach(() => {
  createMutate.mockClear();
  updateMutate.mockClear();
});

describe('InstallmentPlanFormModal', () => {
  it('submits a standalone plan with the write payload', async () => {
    const user = userEvent.setup();
    renderWithProviders(<InstallmentPlanFormModal open plan={null} onClose={vi.fn()} />);

    await user.type(screen.getByLabelText('Descrição'), 'IPTU 2026');
    await user.clear(screen.getByLabelText('Valor total'));
    await user.type(screen.getByLabelText('Valor total'), '1500');
    await user.clear(screen.getByLabelText('Nº de parcelas'));
    await user.type(screen.getByLabelText('Nº de parcelas'), '3');
    await user.type(screen.getByLabelText('Primeira parcela'), '2026-07-10');

    await user.click(screen.getByRole('button', { name: 'Criar' }));

    await waitFor(() => expect(createMutate).toHaveBeenCalledTimes(1));
    const [payload] = createMutate.mock.calls[0] as [Record<string, unknown>];
    expect(payload).toMatchObject({
      description: 'IPTU 2026',
      total_amount: 1500,
      installment_count: 3,
      start_due_date: '2026-07-10',
      embedded: false,
      linked_billing_account_id: null,
      lifecycle_state: 'active',
    });
  });

  it('reveals and requires the billing account when embedded is on', async () => {
    const user = userEvent.setup();
    renderWithProviders(<InstallmentPlanFormModal open plan={null} onClose={vi.fn()} />);

    // The linked-account select is hidden while embedded is off.
    expect(screen.queryByText('Conta recorrente vinculada')).not.toBeInTheDocument();

    await user.type(screen.getByLabelText('Descrição'), 'Parcela embutida');
    await user.type(screen.getByLabelText('Primeira parcela'), '2026-07-10');
    await user.click(screen.getByLabelText('Parcela embutida'));

    // Now the field appears.
    expect(await screen.findByText('Conta recorrente vinculada')).toBeInTheDocument();

    // Submitting without a linked account is blocked by the superRefine (PT message).
    await user.click(screen.getByRole('button', { name: 'Criar' }));
    expect(
      await screen.findByText('Conta recorrente vinculada é obrigatória para parcela embutida'),
    ).toBeInTheDocument();
    expect(createMutate).not.toHaveBeenCalled();
  });

  it('blocks submission and shows a PT message when the description is empty', async () => {
    const user = userEvent.setup();
    renderWithProviders(<InstallmentPlanFormModal open plan={null} onClose={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: 'Criar' }));
    expect(await screen.findByText('Descrição é obrigatória')).toBeInTheDocument();
    expect(createMutate).not.toHaveBeenCalled();
  });

  it('pre-fills fields on edit and calls the update mutation', async () => {
    const user = userEvent.setup();
    const plan: InstallmentPlan = {
      id: 1,
      description: 'IPTU 2026',
      total_amount: 1500,
      installment_count: 3,
      start_due_date: '2026-07-10',
      default_due_day: 10,
      lifecycle_state: 'active',
      embedded: false,
      category: null,
      category_id: null,
      building: null,
      building_id: null,
      linked_billing_account: null,
      linked_billing_account_id: null,
      installments: [],
      notes: '',
    };
    renderWithProviders(<InstallmentPlanFormModal open plan={plan} onClose={vi.fn()} />);

    expect(screen.getByLabelText('Descrição')).toHaveValue('IPTU 2026');
    await user.click(screen.getByRole('button', { name: 'Atualizar' }));

    await waitFor(() => expect(updateMutate).toHaveBeenCalledTimes(1));
    const [payload] = updateMutate.mock.calls[0] as [Record<string, unknown>];
    expect(payload).toMatchObject({ id: 1, description: 'IPTU 2026' });
    expect(createMutate).not.toHaveBeenCalled();
  });
});
