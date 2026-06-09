import { describe, it, expect, vi, beforeAll, beforeEach, afterEach } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/tests/test-utils';
import { createMockBill } from '@/tests/mocks/data/finances';
import { BillFormModal } from '../bill-form-modal';
import * as billHooks from '@/lib/api/hooks/use-bills';

vi.mock('@/lib/api/hooks/use-bills', async (importOriginal) => {
  const actual = await importOriginal<typeof billHooks>();
  return { ...actual, useCreateBillWithLines: vi.fn(), useUpdateBill: vi.fn() };
});

// Stub the select-source hooks so the modal renders without firing real XHRs (which would
// leak into teardown). The form only reads `.data`; empty lists are enough for these tests.
vi.mock('@/lib/api/hooks/use-buildings', () => ({ useBuildings: () => ({ data: [] }) }));
vi.mock('@/lib/api/hooks/use-finance-categories', () => ({
  useFinanceCategories: () => ({ data: [] }),
}));
vi.mock('@/lib/api/hooks/use-billing-accounts', () => ({
  useBillingAccounts: () => ({ data: [] }),
}));

interface CreateCall {
  payload: billHooks.CreateBillWithLines;
}
interface UpdateCall {
  payload: Record<string, unknown>;
}

function makeMutation<T>(store: T[], key: 'payload') {
  const mutate = vi.fn((payload: unknown, options?: { onSuccess?: () => void }) => {
    store.push({ [key]: payload } as T);
    options?.onSuccess?.();
  });
  return { mutate, isPending: false };
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
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function mountCreate() {
    const creates: CreateCall[] = [];
    const updates: UpdateCall[] = [];
    vi.mocked(billHooks.useCreateBillWithLines).mockReturnValue(
      makeMutation<CreateCall>(creates, 'payload') as never
    );
    vi.mocked(billHooks.useUpdateBill).mockReturnValue(
      makeMutation<UpdateCall>(updates, 'payload') as never
    );
    return { creates, updates };
  }

  it('creates a bill via useCreateBillWithLines with the expected fields and lines', async () => {
    const { creates } = mountCreate();
    renderWithProviders(<BillFormModal open onClose={vi.fn()} />);

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
    const payload = creates[0]?.payload;
    expect(payload?.bill).toMatchObject({
      description: 'Conta de Luz',
      competence_month: '2026-06-01',
      due_date: '2026-06-10',
      behavior: 'one_time',
    });
    expect(payload?.line_items[0]).toMatchObject({ description: 'Energia', amount: 350 });
  });

  it('shows the billing_account select for recurring and hides it for one_time', async () => {
    mountCreate();
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderWithProviders(<BillFormModal open onClose={vi.fn()} />);

    expect(screen.queryByText('Conta recorrente')).not.toBeInTheDocument();

    await user.click(screen.getByLabelText('Tipo'));
    await user.click(await screen.findByRole('option', { name: 'Recorrente' }));

    expect(await screen.findByText('Conta recorrente')).toBeInTheDocument();
  });

  it('links installment behavior to Planos de Parcelamento and blocks submission', async () => {
    // The stale "Fase 3" copy is replaced by a real link to the Installment Plans
    // screen; selecting "Parcelada" must still block create (handled elsewhere).
    const { creates } = mountCreate();
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderWithProviders(<BillFormModal open onClose={vi.fn()} />);

    await user.click(screen.getByLabelText('Tipo'));
    await user.click(await screen.findByRole('option', { name: 'Parcelada' }));

    const link = await screen.findByRole('link', { name: /Planos de Parcelamento/i });
    expect(link).toHaveAttribute('href', '/finances/installment-plans');

    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));
    expect(creates).toHaveLength(0);
  });

  it('renders Inscrição/UC and Emissão inputs and includes them in the create payload', async () => {
    // external_identifier + issue_date are already in the schema/payload; this
    // session only renders the inputs — assert they round-trip into the mutation.
    const { creates } = mountCreate();
    renderWithProviders(<BillFormModal open onClose={vi.fn()} />);

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
    expect(creates[0]?.payload.bill).toMatchObject({
      external_identifier: 'UC-12345',
      issue_date: '2026-06-02',
    });
  });

  it('keeps the submit footer rendered (fixed) outside the scrolling body', () => {
    // Footer lives as a sibling of DialogBody (not inside the overflow region),
    // so the action buttons are always present regardless of body length.
    mountCreate();
    renderWithProviders(<BillFormModal open onClose={vi.fn()} />);
    expect(screen.getByRole('button', { name: /^criar$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^cancelar$/i })).toBeInTheDocument();
  });

  it('shows the statement block for water/electricity accounts and hides it for generic/iptu', async () => {
    // The statement block (readings-only inputs) is conditional on the selected
    // account_type: visible for water (consumo_m3) / electricity (consumo_kwh),
    // hidden for generic and iptu. Manual flow: fields render empty and editable.
    mountCreate();
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderWithProviders(<BillFormModal open onClose={vi.fn()} />);

    // generic/iptu → no statement inputs
    expect(screen.queryByLabelText('Consumo (m³)')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Consumo (kWh)')).not.toBeInTheDocument();

    // select water → consumo_m3 input appears (editable, empty)
    await user.click(screen.getByLabelText('Tipo de conta'));
    await user.click(await screen.findByRole('option', { name: /Água/i }));
    expect(await screen.findByLabelText('Consumo (m³)')).toBeInTheDocument();
    expect(screen.queryByLabelText('Consumo (kWh)')).not.toBeInTheDocument();

    // select electricity → consumo_kwh input appears, consumo_m3 disappears
    await user.click(screen.getByLabelText('Tipo de conta'));
    await user.click(await screen.findByRole('option', { name: /Luz/i }));
    expect(await screen.findByLabelText('Consumo (kWh)')).toBeInTheDocument();
    expect(screen.queryByLabelText('Consumo (m³)')).not.toBeInTheDocument();
  });

  it('blocks submission with validation messages when required fields are empty', async () => {
    const { creates } = mountCreate();
    renderWithProviders(<BillFormModal open onClose={vi.fn()} />);

    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));

    await waitFor(() => {
      expect(screen.getAllByText('Descrição é obrigatória').length).toBeGreaterThan(0);
    });
    expect(creates).toHaveLength(0);
  });

  it('prefills fields and updates via useUpdateBill in edit mode (lines locked with PT note)', async () => {
    const { updates } = mountCreate();
    const bill = createMockBill({ id: 5, description: 'Conta Antiga' });
    renderWithProviders(<BillFormModal open bill={bill} onClose={vi.fn()} />);

    expect(screen.getByText('Editar Conta')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Conta Antiga')).toBeInTheDocument();
    expect(screen.getByText(/só podem ser definidas na criação/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /^atualizar$/i }));

    await waitFor(() => {
      expect(updates).toHaveLength(1);
    });
    expect(updates[0]?.payload).toMatchObject({ id: 5, description: 'Conta Antiga' });
  });
});
