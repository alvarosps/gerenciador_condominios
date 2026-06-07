import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/tests/test-utils';
import type { Installment } from '@/lib/schemas/finances/installment-plan.schema';
import { InstallmentScheduleField } from '../installment-schedule-field';

const updateMutate = vi.fn();

vi.mock('@/lib/api/hooks/use-installment-plans', () => ({
  useUpdateInstallment: () => ({ mutate: updateMutate, isPending: false }),
}));

beforeEach(() => {
  updateMutate.mockClear();
});

const installments: Installment[] = [
  { id: 2, plan: 1, number: 2, due_date: '2026-08-10', amount: 500, is_overdue: false },
  { id: 1, plan: 1, number: 1, due_date: '2026-07-10', amount: 500, is_overdue: true },
];

describe('InstallmentScheduleField', () => {
  it('renders installments ordered by number with split dates and currency', () => {
    renderWithProviders(<InstallmentScheduleField installments={installments} isAdmin />);

    const rows = screen.getAllByText(/^Parcela /);
    expect(rows[0]).toHaveTextContent('Parcela 1');
    expect(rows[1]).toHaveTextContent('Parcela 2');
    expect(screen.getByText('10/07/2026')).toBeInTheDocument();
    expect(screen.getAllByText('R$ 500,00').length).toBeGreaterThan(0);
  });

  it('marks an overdue installment with a "Vencida" badge', () => {
    renderWithProviders(<InstallmentScheduleField installments={installments} isAdmin />);
    expect(screen.getByText('Vencida')).toBeInTheDocument();
  });

  it('does not offer add/remove buttons (installments are materialized by the service)', () => {
    renderWithProviders(<InstallmentScheduleField installments={installments} isAdmin />);
    expect(screen.queryByRole('button', { name: /adicionar parcela/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /remover parcela/i })).not.toBeInTheDocument();
  });

  it('PATCHes the amount when an installment is edited', async () => {
    const user = userEvent.setup();
    renderWithProviders(<InstallmentScheduleField installments={installments} isAdmin />);

    const [firstEdit] = screen.getAllByRole('button', { name: 'Editar parcela' });
    if (!firstEdit) throw new Error('No edit button found');
    await user.click(firstEdit);

    const amountInput = screen.getByLabelText('Valor da parcela');
    await user.clear(amountInput);
    await user.type(amountInput, '620');
    await user.click(screen.getByRole('button', { name: 'Salvar parcela' }));

    await waitFor(() => expect(updateMutate).toHaveBeenCalledTimes(1));
    const [payload] = updateMutate.mock.calls[0] as [Record<string, unknown>];
    expect(payload).toMatchObject({ id: 1, amount: 620 });
  });

  it('hides the edit affordance for non-admins', () => {
    renderWithProviders(<InstallmentScheduleField installments={installments} isAdmin={false} />);
    expect(screen.queryByRole('button', { name: 'Editar parcela' })).not.toBeInTheDocument();
  });

  it('shows a PT empty state when there are no installments', () => {
    renderWithProviders(<InstallmentScheduleField installments={[]} isAdmin />);
    expect(
      screen.getByText(/nenhuma parcela materializada ainda/i),
    ).toBeInTheDocument();
  });
});
