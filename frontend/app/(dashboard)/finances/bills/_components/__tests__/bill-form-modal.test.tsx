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
      makeMutation<CreateCall>(creates, 'payload') as never,
    );
    vi.mocked(billHooks.useUpdateBill).mockReturnValue(
      makeMutation<UpdateCall>(updates, 'payload') as never,
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

  it('blocks installment behavior with a Portuguese Phase 3 note', async () => {
    const { creates } = mountCreate();
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderWithProviders(<BillFormModal open onClose={vi.fn()} />);

    await user.click(screen.getByLabelText('Tipo'));
    await user.click(await screen.findByRole('option', { name: 'Parcelada' }));

    expect(await screen.findByText(/Fase 3/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));
    expect(creates).toHaveLength(0);
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
