import { describe, it, expect, beforeAll } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import {
  createMockBill,
  createMockBillingAccount,
  createMockParsedInvoice,
} from '@/tests/mocks/data/finances';
import { billSchema } from '@/lib/schemas/finances/bill.schema';
import { billingAccountSchema } from '@/lib/schemas/finances/billing-account.schema';
import { BillFormModal } from '../bill-form-modal';

// Real hooks (useCreateBillWithLines / useUpdateBill / useUpdateBillWithLines) hit MSW; the
// select-source hooks (buildings / finance-categories / billing-accounts) hit MSW too. The default
// handlers return data; per-test `server.use` overrides them. Each mutation is spied via an MSW
// request-body capture, which exercises the form's real write serialization (line_items + *_id).
const API_BASE = 'http://localhost:8008/api';

interface CreateBody {
  bill: Record<string, unknown>;
  line_items: { description: string; amount: number; is_offset?: boolean }[];
  statement: Record<string, unknown> | null;
}

// Keep the source-select hooks deterministic: empty lists (the form only reads `.data`).
function setSourcesEmpty() {
  server.use(
    http.get(`${API_BASE}/buildings/`, () => HttpResponse.json([])),
    http.get(`${API_BASE}/finances/finance-categories/`, () => HttpResponse.json([])),
    http.get(`${API_BASE}/finances/billing-accounts/`, () => HttpResponse.json([]))
  );
}

// Spy create_with_lines via an MSW request-body capture.
function spyCreate() {
  const bodies: CreateBody[] = [];
  server.use(
    http.post(`${API_BASE}/finances/bills/create_with_lines/`, async ({ request }) => {
      bodies.push((await request.json()) as CreateBody);
      return HttpResponse.json(createMockBill({ id: 99 }), { status: 201 });
    })
  );
  return bodies;
}

// Spy the edit-mode PUT (useUpdateBill) via an MSW request-body capture.
function spyUpdate() {
  const bodies: (Record<string, unknown> & { id: number })[] = [];
  server.use(
    http.put(`${API_BASE}/finances/bills/:id/`, async ({ params, request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      bodies.push({ ...body, id: Number(params.id) });
      return HttpResponse.json(createMockBill({ id: Number(params.id) }));
    })
  );
  return bodies;
}

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

describe('BillFormModal', () => {
  it('creates a bill via useCreateBillWithLines with the expected fields and lines', async () => {
    setSourcesEmpty();
    const creates = spyCreate();
    const { queryClient } = renderWithProviders(<BillFormModal open onClose={() => undefined} />);

    fireEvent.change(screen.getByPlaceholderText('Descrição da conta'), {
      target: { value: 'Conta de Luz' },
    });
    fireEvent.change(screen.getByLabelText('Competência'), { target: { value: '2026-06-01' } });
    fireEvent.change(screen.getByLabelText('Vencimento'), { target: { value: '2026-06-10' } });

    // Fill the single default line item.
    fireEvent.change(screen.getByPlaceholderText('Ex: Consumo de energia'), {
      target: { value: 'Energia' },
    });
    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '350' } });

    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));

    await waitFor(() => {
      expect(creates).toHaveLength(1);
    });
    expect(creates[0]?.bill).toMatchObject({
      description: 'Conta de Luz',
      competence_month: '2026-06-01',
      due_date: '2026-06-10',
      behavior: 'one_time',
    });
    expect(creates[0]?.line_items[0]).toMatchObject({ description: 'Energia', amount: 350 });

    await waitForQueriesToSettle(queryClient);
  });

  it('shows the billing_account select for recurring and hides it for one_time', async () => {
    setSourcesEmpty();
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const { queryClient } = renderWithProviders(<BillFormModal open onClose={() => undefined} />);

    expect(screen.queryByText('Conta recorrente')).not.toBeInTheDocument();

    await user.click(screen.getByLabelText('Tipo'));
    await user.click(await screen.findByRole('option', { name: 'Recorrente' }));

    expect(await screen.findByText('Conta recorrente')).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('links installment behavior to Planos de Parcelamento and blocks submission', async () => {
    // The stale "Fase 3" copy is replaced by a real link to the Installment Plans
    // screen; selecting "Parcelada" must still block create (handled elsewhere).
    setSourcesEmpty();
    const creates = spyCreate();
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const { queryClient } = renderWithProviders(<BillFormModal open onClose={() => undefined} />);

    await user.click(screen.getByLabelText('Tipo'));
    await user.click(await screen.findByRole('option', { name: 'Parcelada' }));

    const link = await screen.findByRole('link', { name: /Planos de Parcelamento/i });
    expect(link).toHaveAttribute('href', '/finances/installment-plans');

    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));
    expect(creates).toHaveLength(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('renders Inscrição/UC and Emissão inputs and includes them in the create payload', async () => {
    // external_identifier + issue_date are already in the schema/payload; this
    // session only renders the inputs — assert they round-trip into the mutation.
    setSourcesEmpty();
    const creates = spyCreate();
    const { queryClient } = renderWithProviders(<BillFormModal open onClose={() => undefined} />);

    fireEvent.change(screen.getByPlaceholderText('Descrição da conta'), {
      target: { value: 'Conta de Água' },
    });
    fireEvent.change(screen.getByLabelText('Competência'), { target: { value: '2026-06-01' } });
    fireEvent.change(screen.getByLabelText('Vencimento'), { target: { value: '2026-06-10' } });
    fireEvent.change(screen.getByLabelText('Inscrição / UC (opcional)'), {
      target: { value: 'UC-12345' },
    });
    fireEvent.change(screen.getByLabelText('Emissão (opcional)'), {
      target: { value: '2026-06-02' },
    });
    fireEvent.change(screen.getByPlaceholderText('Ex: Consumo de energia'), {
      target: { value: 'Consumo' },
    });
    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '120' } });

    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));

    await waitFor(() => {
      expect(creates).toHaveLength(1);
    });
    expect(creates[0]?.bill).toMatchObject({
      external_identifier: 'UC-12345',
      issue_date: '2026-06-02',
    });

    await waitForQueriesToSettle(queryClient);
  });

  it('keeps the submit footer rendered (fixed) outside the scrolling body', async () => {
    // Footer lives as a sibling of DialogBody (not inside the overflow region),
    // so the action buttons are always present regardless of body length.
    setSourcesEmpty();
    const { queryClient } = renderWithProviders(<BillFormModal open onClose={() => undefined} />);
    expect(screen.getByRole('button', { name: /^criar$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^cancelar$/i })).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('hides the statement block on the manual create flow even for water/electricity', async () => {
    // Readings have no leg on the manual create/update payload — they would be silently dropped.
    // So the statement block is gated on the parser-draft flow (isDraft) and never renders on a
    // manual "Nova Conta", regardless of the selected account_type.
    setSourcesEmpty();
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const { queryClient } = renderWithProviders(<BillFormModal open onClose={() => undefined} />);

    expect(screen.queryByLabelText('Consumo (m³)')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Consumo (kWh)')).not.toBeInTheDocument();

    await user.click(screen.getByLabelText('Tipo de conta'));
    await user.click(await screen.findByRole('option', { name: /Água/i }));
    expect(screen.queryByLabelText('Consumo (m³)')).not.toBeInTheDocument();

    await user.click(screen.getByLabelText('Tipo de conta'));
    await user.click(await screen.findByRole('option', { name: /Luz/i }));
    expect(screen.queryByLabelText('Consumo (kWh)')).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('shows the statement block on an imported electricity draft and sends the reading', async () => {
    setSourcesEmpty();
    const creates = spyCreate();
    const draft = createMockParsedInvoice({
      matched_account: billingAccountSchema.parse(
        createMockBillingAccount({ id: 7, account_type: 'electricity' })
      ),
      statement: { consumo_kwh: 320, classe: 'Residencial', bandeira: 'Verde' },
    });
    const { queryClient } = renderWithProviders(
      <BillFormModal open draft={draft} onClose={() => undefined} />
    );

    // The draft (account_type electricity) renders the readings block, prefilled from the draft.
    expect(await screen.findByLabelText('Consumo (kWh)')).toBeInTheDocument();
    expect(screen.getByLabelText('Consumo (kWh)')).toHaveValue('320');

    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));

    await waitFor(() => {
      expect(creates).toHaveLength(1);
    });
    // A matched account is bound, so the statement IS sent (kind=electricity, consumo_kwh=320).
    expect(creates[0]?.statement).toMatchObject({ kind: 'electricity', consumo_kwh: 320 });

    await waitForQueriesToSettle(queryClient);
  });

  it('drops the statement on a no-match draft (billing_account_id null) but still creates', async () => {
    setSourcesEmpty();
    const creates = spyCreate();
    const draft = createMockParsedInvoice({
      matched_account: null, // no-match: billing_account_id resolves to null
      statement: { consumo_kwh: 99, classe: 'Residencial', bandeira: 'Verde' },
      warnings: ['Nenhuma conta encontrada.'],
    });
    const { queryClient } = renderWithProviders(
      <BillFormModal open draft={draft} onClose={() => undefined} />
    );

    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));

    await waitFor(() => {
      expect(creates).toHaveLength(1);
    });
    // No account to type the statement → it must NOT be sent (backend would 400 on a null account).
    expect(creates[0]?.statement).toBeNull();
    expect(creates[0]?.bill).toMatchObject({ billing_account_id: null });

    await waitForQueriesToSettle(queryClient);
  });

  it('blocks submission with validation messages when required fields are empty', async () => {
    setSourcesEmpty();
    const creates = spyCreate();
    const { queryClient } = renderWithProviders(<BillFormModal open onClose={() => undefined} />);

    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));

    await waitFor(() => {
      expect(screen.getAllByText('Descrição é obrigatória').length).toBeGreaterThan(0);
    });
    expect(creates).toHaveLength(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('prefills fields and updates via useUpdateBill in edit mode (lines locked with PT note)', async () => {
    setSourcesEmpty();
    const updates = spyUpdate();
    const bill = billSchema.parse(createMockBill({ id: 5, description: 'Conta Antiga' }));
    const { queryClient } = renderWithProviders(
      <BillFormModal open bill={bill} onClose={() => undefined} />
    );

    expect(screen.getByText('Editar Conta')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Conta Antiga')).toBeInTheDocument();
    expect(screen.getByText(/só podem ser definidas na criação/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /^atualizar$/i }));

    await waitFor(() => {
      expect(updates).toHaveLength(1);
    });
    expect(updates[0]).toMatchObject({ id: 5, description: 'Conta Antiga' });

    await waitForQueriesToSettle(queryClient);
  });
});
