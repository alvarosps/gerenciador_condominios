import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockEmployee } from '@/tests/mocks/data/finances';
import { createMockPerson } from '@/tests/mocks/data/persons';
import { createMockLease } from '@/tests/mocks/data/leases';
import { employeeSchema, type Employee } from '@/lib/schemas/finances/employee.schema';
import { toast } from 'sonner';
import { EmployeeFormModal } from '../employee-form-modal';

const API_BASE = 'http://localhost:8008/api';

// The modal is exercised through the real create/update mutations hitting MSW (the HTTP boundary)
// and the real usePersons/useLeases queries; no hook is mocked. `toast` is the global sonner mock.
function setSources() {
  server.use(
    http.get(`${API_BASE}/persons/`, () =>
      HttpResponse.json([createMockPerson({ id: 2, name: 'Rosa' })])
    ),
    // createMockLease's default apartment (mockApartments[0]) has number 101 → renders "Apto 101".
    http.get(`${API_BASE}/leases/`, () => HttpResponse.json([createMockLease({ id: 7 })]))
  );
}

/** Spy the create POST; pushes each request body and returns a parseable raw employee. */
function spyCreate() {
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.post(`${API_BASE}/finances/employees/`, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      bodies.push(body);
      return HttpResponse.json(createMockEmployee({ id: 99, ...body }), { status: 201 });
    })
  );
  return bodies;
}

/** Spy the update PATCH; pushes each request body and returns a parseable raw employee. */
function spyUpdate(id: number) {
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.patch(`${API_BASE}/finances/employees/${id}/`, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      bodies.push(body);
      return HttpResponse.json(createMockEmployee({ id, ...body }));
    })
  );
  return bodies;
}

beforeEach(() => {
  vi.mocked(toast.success).mockReset();
  vi.mocked(toast.error).mockReset();
  setSources();
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
    const bodies = spyCreate();
    renderWithProviders(<EmployeeFormModal open employee={null} onClose={vi.fn()} />);

    // Switch payment type to "Variável".
    await user.click(screen.getByLabelText('Tipo de pagamento'));
    await user.click(await screen.findByRole('option', { name: 'Variável' }));

    // The salary field disappears.
    await waitFor(() => expect(screen.queryByLabelText('Salário base')).not.toBeInTheDocument());

    await user.type(screen.getByLabelText('Nome'), 'Raymel');
    await user.click(screen.getByRole('button', { name: 'Criar' }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({
      name: 'Raymel',
      payment_type: 'variable',
      base_salary: null,
    });
  });

  it('requires base_salary for fixed type (PT validation blocks submit)', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const bodies = spyCreate();
    renderWithProviders(<EmployeeFormModal open employee={null} onClose={vi.fn()} />);

    await user.type(screen.getByLabelText('Nome'), 'Adriana');
    // base_salary visible by default (fixed); clear it to trigger the rule.
    await user.clear(screen.getByLabelText('Salário base'));
    await user.click(screen.getByRole('button', { name: 'Criar' }));

    expect(
      await screen.findByText('Salário base é obrigatório para funcionário fixo ou misto')
    ).toBeInTheDocument();
    expect(bodies).toHaveLength(0);
  });

  it('submits a mixed employee linked to person + lease (Rosa-like) with _id', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const bodies = spyCreate();
    const { queryClient } = renderWithProviders(
      <EmployeeFormModal open employee={null} onClose={vi.fn()} />
    );
    // The person/lease source selects only render their options once the queries resolve; settle
    // them before opening so Radix mounts the items.
    await waitForQueriesToSettle(queryClient);

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

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({
      payment_type: 'mixed',
      base_salary: 850,
      person_id: 2,
      lease_id: 7,
    });
  });

  it('pre-fills fields on edit and calls the update mutation', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const employee: Employee = employeeSchema.parse(
      createMockEmployee({ id: 1, name: 'Adriana', payment_type: 'fixed', base_salary: '1320.00' })
    );
    const updateBodies = spyUpdate(1);
    const createBodies = spyCreate();
    renderWithProviders(<EmployeeFormModal open employee={employee} onClose={vi.fn()} />);

    expect(screen.getByLabelText('Nome')).toHaveValue('Adriana');
    await user.click(screen.getByRole('button', { name: 'Atualizar' }));

    await waitFor(() => expect(updateBodies).toHaveLength(1));
    expect(updateBodies[0]).toMatchObject({ name: 'Adriana' });
    expect(createBodies).toHaveLength(0);
  });
});
