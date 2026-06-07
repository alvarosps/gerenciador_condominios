import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/tests/test-utils';
import type { Employee } from '@/lib/schemas/finances/employee.schema';
import { EmployeeFormModal } from '../employee-form-modal';

const createMutate = vi.fn();
const updateMutate = vi.fn();

vi.mock('@/lib/api/hooks/use-employees', () => ({
  useCreateEmployee: () => ({ mutate: createMutate, isPending: false }),
  useUpdateEmployee: () => ({ mutate: updateMutate, isPending: false }),
}));

vi.mock('@/lib/api/hooks/use-persons', () => ({
  usePersons: () => ({ data: [{ id: 2, name: 'Rosa' }] }),
}));

vi.mock('@/lib/api/hooks/use-leases', () => ({
  useLeases: () => ({ data: [{ id: 7, apartment: { id: 1, number: '101' } }] }),
}));

beforeEach(() => {
  createMutate.mockClear();
  updateMutate.mockClear();
});

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

describe('EmployeeFormModal', () => {
  it('hides base_salary for variable type and submits without it (Raymel)', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderWithProviders(<EmployeeFormModal open employee={null} onClose={vi.fn()} />);

    // Switch payment type to "Variável".
    await user.click(screen.getByLabelText('Tipo de pagamento'));
    await user.click(await screen.findByRole('option', { name: 'Variável' }));

    // The salary field disappears.
    await waitFor(() => expect(screen.queryByLabelText('Salário base')).not.toBeInTheDocument());

    await user.type(screen.getByLabelText('Nome'), 'Raymel');
    await user.click(screen.getByRole('button', { name: 'Criar' }));

    await waitFor(() => expect(createMutate).toHaveBeenCalledTimes(1));
    const [payload] = createMutate.mock.calls[0] as [Record<string, unknown>];
    expect(payload).toMatchObject({ name: 'Raymel', payment_type: 'variable', base_salary: null });
  });

  it('requires base_salary for fixed type (PT validation blocks submit)', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderWithProviders(<EmployeeFormModal open employee={null} onClose={vi.fn()} />);

    await user.type(screen.getByLabelText('Nome'), 'Adriana');
    // base_salary visible by default (fixed); clear it to trigger the rule.
    await user.clear(screen.getByLabelText('Salário base'));
    await user.click(screen.getByRole('button', { name: 'Criar' }));

    expect(
      await screen.findByText('Salário base é obrigatório para funcionário fixo ou misto'),
    ).toBeInTheDocument();
    expect(createMutate).not.toHaveBeenCalled();
  });

  it('submits a mixed employee linked to person + lease (Rosa-like) with _id', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderWithProviders(<EmployeeFormModal open employee={null} onClose={vi.fn()} />);

    await user.type(screen.getByLabelText('Nome'), 'Rosa');
    await user.click(screen.getByLabelText('Tipo de pagamento'));
    await user.click(await screen.findByRole('option', { name: 'Misto' }));

    await user.clear(screen.getByLabelText('Salário base'));
    await user.type(screen.getByLabelText('Salário base'), '850');

    await user.click(screen.getByLabelText('Pessoa vinculada (opcional)'));
    await user.click(await screen.findByRole('option', { name: 'Rosa' }));

    await user.click(screen.getByLabelText('Locação vinculada (opcional)'));
    await user.click(await screen.findByRole('option', { name: 'Apto 101' }));

    await user.click(screen.getByRole('button', { name: 'Criar' }));

    await waitFor(() => expect(createMutate).toHaveBeenCalledTimes(1));
    const [payload] = createMutate.mock.calls[0] as [Record<string, unknown>];
    expect(payload).toMatchObject({
      payment_type: 'mixed',
      base_salary: 850,
      person_id: 2,
      lease_id: 7,
    });
  });

  it('pre-fills fields on edit and calls the update mutation', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const employee: Employee = {
      id: 1,
      name: 'Adriana',
      role: 'Faxineira',
      payment_type: 'fixed',
      base_salary: 1320,
      default_due_day: 5,
      is_active: true,
      notes: '',
      person: null,
      person_id: null,
      lease: null,
      lease_id: null,
    };
    renderWithProviders(<EmployeeFormModal open employee={employee} onClose={vi.fn()} />);

    expect(screen.getByLabelText('Nome')).toHaveValue('Adriana');
    await user.click(screen.getByRole('button', { name: 'Atualizar' }));

    await waitFor(() => expect(updateMutate).toHaveBeenCalledTimes(1));
    const [payload] = updateMutate.mock.calls[0] as [Record<string, unknown>];
    expect(payload).toMatchObject({ id: 1, name: 'Adriana' });
    expect(createMutate).not.toHaveBeenCalled();
  });
});
