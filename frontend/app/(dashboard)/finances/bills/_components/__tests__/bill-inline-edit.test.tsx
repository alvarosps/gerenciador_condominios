import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockBill, createMockBillLineItem } from '@/tests/mocks/data/finances';
import { AmountPopover, DueDatePopover, canEditAmountInline } from '../bill-inline-edit';
import type { Bill } from '@/lib/schemas/finances/bill.schema';

const API_BASE = 'http://localhost:8008/api';

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

function spyPatch() {
  const bodies: (Record<string, unknown> & { id: number })[] = [];
  server.use(
    http.patch(`${API_BASE}/finances/bills/:id/`, async ({ params, request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      bodies.push({ ...body, id: Number(params.id) });
      return HttpResponse.json(createMockBill({ id: Number(params.id), ...body }));
    })
  );
  return bodies;
}

function spyUpdateWithLines() {
  const bodies: (Record<string, unknown> & { bill_id: number })[] = [];
  server.use(
    http.post(`${API_BASE}/finances/bills/:id/update_with_lines/`, async ({ params, request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      bodies.push({ ...body, bill_id: Number(params.id) });
      return HttpResponse.json(createMockBill({ id: Number(params.id) }));
    })
  );
  return bodies;
}

describe('DueDatePopover', () => {
  beforeEach(() => {
    vi.mocked(toast.success).mockReset();
    vi.mocked(toast.error).mockReset();
  });

  it('PATCHes only {due_date} to bills/{id}/ and refetches on success', async () => {
    const bodies = spyPatch();
    const bill = createMockBill({ id: 7, due_date: '2026-06-10' }) as unknown as Bill;

    const { queryClient } = renderWithProviders(<DueDatePopover bill={bill} />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    await user.click(screen.getByRole('button', { name: /editar vencimento/i }));

    fireEvent.change(screen.getByLabelText(/novo vencimento/i), {
      target: { value: '2026-06-20' },
    });
    await user.click(screen.getByRole('button', { name: /^salvar$/i }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toEqual({ id: 7, due_date: '2026-06-20' });
    // No money field ever travels through the header PATCH.
    expect(bodies[0]).not.toHaveProperty('amount_total');
    expect(bodies[0]).not.toHaveProperty('line_items');

    await waitForQueriesToSettle(queryClient);
  });

  it('shows an actionable "Abrir fechamento" toast when the PATCH hits a closed month', async () => {
    server.use(
      http.patch(`${API_BASE}/finances/bills/:id/`, () =>
        HttpResponse.json({ detail: 'Competência 06/2026 está fechada.' }, { status: 400 })
      )
    );
    const bill = createMockBill({ id: 7, due_date: '2026-06-10' }) as unknown as Bill;

    const { queryClient } = renderWithProviders(<DueDatePopover bill={bill} />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    await user.click(screen.getByRole('button', { name: /editar vencimento/i }));

    fireEvent.change(screen.getByLabelText(/novo vencimento/i), {
      target: { value: '2026-06-20' },
    });
    await user.click(screen.getByRole('button', { name: /^salvar$/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        'Competência 06/2026 está fechada.',
        expect.objectContaining({
          action: expect.objectContaining({ label: 'Abrir fechamento' }) as unknown,
        })
      );
    });

    await waitForQueriesToSettle(queryClient);
  });
});

describe('AmountPopover', () => {
  beforeEach(() => {
    vi.mocked(toast.success).mockReset();
    vi.mocked(toast.error).mockReset();
  });

  it('updates the single non-installment line via update_with_lines preserving its fields', async () => {
    const bodies = spyUpdateWithLines();
    const line = createMockBillLineItem({
      id: 1,
      description: 'Consumo de energia',
      amount: '350.00',
      is_offset: false,
    });
    const bill = createMockBill({ id: 7, line_items: [line] }) as unknown as Bill;

    const { queryClient } = renderWithProviders(<AmountPopover bill={bill} />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    await user.click(screen.getByRole('button', { name: /editar valor/i }));

    fireEvent.change(screen.getByLabelText(/novo valor/i), { target: { value: '420' } });
    await user.click(screen.getByRole('button', { name: /^salvar$/i }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]?.bill_id).toBe(7);
    expect(bodies[0]?.line_items).toEqual([
      { description: 'Consumo de energia', amount: 420, is_offset: false },
    ]);

    await waitForQueriesToSettle(queryClient);
  });

  it('is not offered for bills with multiple lines, a consumption billing_account (may carry an embedded installment line) or a statement', () => {
    const multiLine = createMockBill({
      id: 1,
      line_items: [createMockBillLineItem({ id: 1 }), createMockBillLineItem({ id: 2 })],
    }) as unknown as Bill;
    expect(canEditAmountInline(multiLine)).toBe(false);

    // A recurring bill tied to a WATER/ELECTRICITY/INTERNET account can carry an embedded
    // installment line even with a single line total (zero-seed + embedded parcela, S41) — the
    // read serializer never exposes BillLineItem.installment, so the consumption account_type is
    // the only sound signal to keep that line un-editable inline (never risk a silent money edit
    // on an embedded parcela).
    const consumptionBill = createMockBill({
      id: 2,
      billing_account: {
        id: 1,
        name: 'Água 836',
        account_type: 'water',
        external_identifier: 'UC-1',
        default_due_day: 10,
        expected_amount: '0.00',
        lifecycle_state: 'active',
      } as never,
      line_items: [createMockBillLineItem({ id: 1 })],
    }) as unknown as Bill;
    expect(canEditAmountInline(consumptionBill)).toBe(false);

    const waterBill = {
      ...createMockBill({ id: 3 }),
      water_statement: {
        consumo_m3: 10,
        leitura_anterior: 100,
        leitura_atual: 110,
        leitura_dias: 30,
        data_leitura: '2026-06-01',
        agua_status: 'active',
        esgoto_status: 'active',
      },
    } as unknown as Bill;
    expect(canEditAmountInline(waterBill)).toBe(false);

    const eligible = createMockBill({ id: 4, line_items: [createMockBillLineItem({ id: 1 })] });
    expect(canEditAmountInline(eligible as unknown as Bill)).toBe(true);

    // A generic/IPTU recurring account is never embedded-eligible (embedded ⇒ consumption type),
    // so a single-line bill on that account is safely editable too.
    const genericRecurring = createMockBill({
      id: 5,
      billing_account: {
        id: 2,
        name: 'Taxa condominial',
        account_type: 'generic',
        external_identifier: '',
        default_due_day: 10,
        expected_amount: '350.00',
        lifecycle_state: 'active',
      } as never,
      line_items: [createMockBillLineItem({ id: 1 })],
    }) as unknown as Bill;
    expect(canEditAmountInline(genericRecurring)).toBe(true);
  });

  it('never issues a PATCH when editing the amount', async () => {
    const patchBodies = spyPatch();
    const updateBodies = spyUpdateWithLines();
    const bill = createMockBill({
      id: 7,
      line_items: [createMockBillLineItem({ id: 1 })],
    }) as unknown as Bill;

    const { queryClient } = renderWithProviders(<AmountPopover bill={bill} />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    await user.click(screen.getByRole('button', { name: /editar valor/i }));

    fireEvent.change(screen.getByLabelText(/novo valor/i), { target: { value: '500' } });
    await user.click(screen.getByRole('button', { name: /^salvar$/i }));

    await waitFor(() => expect(updateBodies).toHaveLength(1));
    expect(patchBodies).toHaveLength(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('shows a PT validation message and never submits when the value is zero or invalid (review round 1 minor)', async () => {
    const updateBodies = spyUpdateWithLines();
    const bill = createMockBill({
      id: 7,
      line_items: [createMockBillLineItem({ id: 1 })],
    }) as unknown as Bill;

    renderWithProviders(<AmountPopover bill={bill} />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    await user.click(screen.getByRole('button', { name: /editar valor/i }));

    fireEvent.change(screen.getByLabelText(/novo valor/i), { target: { value: '0' } });
    await user.click(screen.getByRole('button', { name: /^salvar$/i }));

    expect(await screen.findByText(/o valor deve ser maior que zero/i)).toBeInTheDocument();
    expect(updateBodies).toHaveLength(0);
  });

  it('shows an actionable "Abrir fechamento" toast when update_with_lines hits a closed month', async () => {
    server.use(
      http.post(`${API_BASE}/finances/bills/:id/update_with_lines/`, () =>
        HttpResponse.json({ detail: 'Competência 06/2026 está fechada.' }, { status: 400 })
      )
    );
    const line = createMockBillLineItem({ id: 1, amount: '350.00' });
    const bill = createMockBill({ id: 7, line_items: [line] }) as unknown as Bill;

    const { queryClient } = renderWithProviders(<AmountPopover bill={bill} />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    await user.click(screen.getByRole('button', { name: /editar valor/i }));

    fireEvent.change(screen.getByLabelText(/novo valor/i), { target: { value: '420' } });
    await user.click(screen.getByRole('button', { name: /^salvar$/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        'Competência 06/2026 está fechada.',
        expect.objectContaining({
          action: expect.objectContaining({ label: 'Abrir fechamento' }) as unknown,
        })
      );
    });

    await waitForQueriesToSettle(queryClient);
  });
});
