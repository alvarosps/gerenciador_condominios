import { describe, it, expect, vi, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import { renderWithProviders } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import type { Installment } from '@/lib/schemas/finances/installment-plan.schema';
import { installmentSchema } from '@/lib/schemas/finances/installment-plan.schema';
import { createMockInstallment } from '@/tests/mocks/data/finances';
import { InstallmentScheduleField } from '../installment-schedule-field';

const API_BASE = 'http://localhost:8008/api';

// The schedule edit is exercised through the real useUpdateInstallment mutation hitting MSW (the
// HTTP boundary) — no hook is mocked. `installments` are typed parsed props, so each is parsed
// through the real schema. `toast` is the global sonner mock from tests/setup.ts.
const installments: Installment[] = [
  installmentSchema.parse(
    createMockInstallment({ id: 2, plan: 1, number: 2, due_date: '2026-08-10', amount: '500.00' })
  ),
  installmentSchema.parse(
    createMockInstallment({ id: 1, plan: 1, number: 1, due_date: '2026-07-10', amount: '500.00' })
  ),
];

function spyUpdate(installmentId: number) {
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.patch(`${API_BASE}/finances/installments/${installmentId}/`, async ({ request }) => {
      bodies.push((await request.json()) as Record<string, unknown>);
      return HttpResponse.json(createMockInstallment({ id: installmentId, amount: '620.00' }));
    })
  );
  return bodies;
}

describe('InstallmentScheduleField', () => {
  beforeEach(() => {
    vi.mocked(toast.success).mockReset();
    vi.mocked(toast.error).mockReset();
  });

  it('renders installments ordered by number with split dates and currency', () => {
    renderWithProviders(<InstallmentScheduleField installments={installments} isAdmin />);

    const rows = screen.getAllByText(/^Parcela /);
    expect(rows[0]).toHaveTextContent('Parcela 1');
    expect(rows[1]).toHaveTextContent('Parcela 2');
    expect(screen.getByText('10/07/2026')).toBeInTheDocument();
    expect(screen.getAllByText('R$ 500,00').length).toBeGreaterThan(0);
  });

  it('marks an overdue installment with a "Vencida" badge', () => {
    const withOverdue: Installment[] = [
      installmentSchema.parse(
        createMockInstallment({ id: 1, number: 1, amount: '500.00', is_overdue: true })
      ),
    ];
    renderWithProviders(<InstallmentScheduleField installments={withOverdue} isAdmin />);
    expect(screen.getByText('Vencida')).toBeInTheDocument();
  });

  it('does not offer add/remove buttons (installments are materialized by the service)', () => {
    renderWithProviders(<InstallmentScheduleField installments={installments} isAdmin />);
    expect(screen.queryByRole('button', { name: /adicionar parcela/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /remover parcela/i })).not.toBeInTheDocument();
  });

  it('PATCHes the amount when an installment is edited', async () => {
    const user = userEvent.setup();
    const bodies = spyUpdate(1);
    renderWithProviders(<InstallmentScheduleField installments={installments} isAdmin />);

    const [firstEdit] = screen.getAllByRole('button', { name: 'Editar parcela' });
    if (!firstEdit) throw new Error('No edit button found');
    await user.click(firstEdit);

    const amountInput = screen.getByLabelText('Valor da parcela');
    await user.clear(amountInput);
    await user.type(amountInput, '620');
    await user.click(screen.getByRole('button', { name: 'Salvar parcela' }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({ amount: 620 });
    await waitFor(() => expect(toast.success).toHaveBeenCalled());
  });

  it('hides the edit affordance for non-admins', () => {
    renderWithProviders(<InstallmentScheduleField installments={installments} isAdmin={false} />);
    expect(screen.queryByRole('button', { name: 'Editar parcela' })).not.toBeInTheDocument();
  });

  it('shows a PT empty state when there are no installments', () => {
    renderWithProviders(<InstallmentScheduleField installments={[]} isAdmin />);
    expect(screen.getByText(/nenhuma parcela materializada ainda/i)).toBeInTheDocument();
  });
});
