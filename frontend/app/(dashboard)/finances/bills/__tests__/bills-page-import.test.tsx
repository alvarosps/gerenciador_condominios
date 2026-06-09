import { describe, it, expect, vi, beforeAll, beforeEach, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, createTestQueryClient } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import {
  createMockBill,
  createMockBillingAccount,
  createMockParsedInvoice,
} from '@/tests/mocks/data/finances';
import BillsPage from '../page';
import * as billHooks from '@/lib/api/hooks/use-bills';
import type { ParsedInvoice } from '@/lib/schemas/finances/invoice-parse.schema';

vi.mock('@/lib/api/hooks/use-bills', async (importOriginal) => {
  const actual = await importOriginal<typeof billHooks>();
  return {
    ...actual,
    useGenerateMonthBills: vi.fn(),
    useParseInvoice: vi.fn(),
    useCreateBillWithLines: vi.fn(),
    useUpdateBillWithLines: vi.fn(),
    useUpdateBill: vi.fn(),
  };
});

vi.mock('@/lib/api/hooks/use-buildings', () => ({ useBuildings: () => ({ data: [] }) }));
vi.mock('@/lib/api/hooks/use-finance-categories', () => ({
  useFinanceCategories: () => ({ data: [] }),
}));

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

function setBillsResponse(bills: unknown[]) {
  server.use(http.get(`${API_BASE}/finances/bills/`, () => HttpResponse.json(bills)));
}

function setBillingAccounts(accounts: unknown[]) {
  server.use(
    http.get(`${API_BASE}/finances/billing-accounts/`, () => HttpResponse.json(accounts)),
  );
}

function setIptuAlerts() {
  server.use(
    http.get(`${API_BASE}/finances/finance-dashboard/iptu_alerts/`, () =>
      HttpResponse.json({ alerts: [], warning_count: 0, critical_count: 0 }),
    ),
  );
}

function setAdmin(isStaff: boolean) {
  useAuthStore.setState({
    user: { id: 1, email: 'a@b.c', first_name: 'A', last_name: 'B', is_staff: isStaff },
    isAuthenticated: true,
  });
}

interface MutationStub<P> {
  mutate: ReturnType<typeof vi.fn>;
  calls: P[];
}

function makeMutation<P>(): MutationStub<P> {
  const calls: P[] = [];
  const mutate = vi.fn((payload: P, options?: { onSuccess?: (data?: unknown) => void }) => {
    calls.push(payload);
    options?.onSuccess?.(createMockBill({ id: 99 }));
  });
  return { mutate, calls };
}

interface MountResult {
  parseCalls: File[];
  createStub: MutationStub<billHooks.CreateBillWithLines>;
  updateStub: MutationStub<billHooks.UpdateBillWithLines>;
}

function mountHooks(draft: ParsedInvoice | null): MountResult {
  const parseCalls: File[] = [];
  const parseMutate = vi.fn((file: File, options?: { onSuccess?: (d: ParsedInvoice) => void }) => {
    parseCalls.push(file);
    if (draft) options?.onSuccess?.(draft);
  });
  vi.mocked(billHooks.useParseInvoice).mockReturnValue({
    mutate: parseMutate,
    isPending: false,
  } as never);

  const createStub = makeMutation<billHooks.CreateBillWithLines>();
  const updateStub = makeMutation<billHooks.UpdateBillWithLines>();
  vi.mocked(billHooks.useCreateBillWithLines).mockReturnValue({
    mutate: createStub.mutate,
    isPending: false,
  } as never);
  vi.mocked(billHooks.useUpdateBillWithLines).mockReturnValue({
    mutate: updateStub.mutate,
    isPending: false,
  } as never);
  vi.mocked(billHooks.useUpdateBill).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as never);
  vi.mocked(billHooks.useGenerateMonthBills).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as never);

  return { parseCalls, createStub, updateStub };
}

function uploadPdf() {
  const input = document.querySelector<HTMLInputElement>('input[type="file"]');
  if (!input) throw new Error('file input not found');
  const file = new File(['%PDF'], 'fatura.pdf', { type: 'application/pdf' });
  fireEvent.change(input, { target: { files: [file] } });
}

describe('BillsPage — import fatura + disambiguated accounts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setIptuAlerts();
    setBillingAccounts([]);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('hides "Importar fatura" and "Nova Conta" for non-admin users', async () => {
    setAdmin(false);
    mountHooks(null);
    setBillsResponse([createMockBill({ id: 1, description: 'Conta de Luz' })]);

    renderWithProviders(<BillsPage />, { queryClient: createTestQueryClient() });

    expect((await screen.findAllByText('Conta de Luz')).length).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: /importar fatura/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /nova conta/i })).not.toBeInTheDocument();
  });

  it('shows "Importar fatura" for admin users', async () => {
    setAdmin(true);
    mountHooks(null);
    setBillsResponse([createMockBill({ id: 1, description: 'Conta de Luz' })]);

    renderWithProviders(<BillsPage />, { queryClient: createTestQueryClient() });

    expect(await screen.findByRole('button', { name: /importar fatura/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /nova conta/i })).toBeInTheDocument();
  });

  it('parsing a PDF opens the bill modal prefilled from the draft (header + lines + locked installment line)', async () => {
    setAdmin(true);
    const draft = createMockParsedInvoice({
      bill: {
        competence_month: '2026-05-01',
        due_date: '2026-05-10',
        external_identifier: 'UC-77',
        behavior: 'recurring',
        account_type: 'water',
        description: 'Conta de Água - 836',
        building_id: null,
        category_id: null,
      },
      line_items: [
        { description: 'Consumo de água', amount: 80, is_offset: false, category_id: null, installment_id: null },
        { description: 'PARCELA 3/59', amount: 12, is_offset: false, category_id: null, installment_id: 42 },
      ],
      statement: {
        consumo_m3: 12,
        leitura_anterior: 100,
        leitura_atual: 112,
        leitura_dias: 30,
        data_leitura: '2026-05-01',
        agua_status: 'active',
        esgoto_status: 'active',
      },
      existing_bill_id: null,
      warnings: ['Aviso de teste'],
    });
    mountHooks(draft);
    setBillsResponse([createMockBill({ id: 1, description: 'Conta de Luz' })]);

    renderWithProviders(<BillsPage />, { queryClient: createTestQueryClient() });

    await screen.findByRole('button', { name: /importar fatura/i });
    uploadPdf();

    // Modal opens with the draft header.
    expect(await screen.findByDisplayValue('Conta de Água - 836')).toBeInTheDocument();
    expect(screen.getByDisplayValue('UC-77')).toBeInTheDocument();
    // Reconciled installment line is rendered locked (disabled input).
    const installmentInput = await screen.findByDisplayValue('PARCELA 3/59');
    expect(installmentInput).toBeDisabled();
    // Statement prefilled (consumo_m3) — scoped to its labelled input.
    expect(screen.getByLabelText('Consumo (m³)')).toHaveValue('12');
    // Warning shown.
    expect(screen.getByText(/Aviso de teste/)).toBeInTheDocument();
  });

  it('renders two same-type accounts with distinct disambiguated labels "name — tipo · external_identifier"', async () => {
    setAdmin(true);
    mountHooks(null);
    setBillsResponse([createMockBill({ id: 1, description: 'Conta de Luz' })]);
    setBillingAccounts([
      createMockBillingAccount({
        id: 1,
        name: 'Conta de Luz - 836',
        account_type: 'electricity',
        external_identifier: '1.273.798.010-05',
      }),
      createMockBillingAccount({
        id: 2,
        name: 'Conta de Luz - 850',
        account_type: 'electricity',
        external_identifier: '9.999.999.999-99',
      }),
    ]);

    renderWithProviders(<BillsPage />, { queryClient: createTestQueryClient() });

    const user = userEvent.setup({ pointerEventsCheck: 0 });
    await user.click(await screen.findByRole('button', { name: /nova conta/i }));
    // Switch to recurring to reveal the billing-account select.
    await user.click(await screen.findByLabelText('Tipo'));
    await user.click(await screen.findByRole('option', { name: 'Recorrente' }));
    await user.click(await screen.findByText('Conta recorrente'));

    const opt1 = await screen.findByRole('option', { name: /Conta de Luz - 836 — Luz · 1\.273\.798\.010-05/ });
    const opt2 = await screen.findByRole('option', { name: /Conta de Luz - 850 — Luz · 9\.999\.999\.999-99/ });
    expect(opt1).toBeInTheDocument();
    expect(opt2).toBeInTheDocument();
    expect(opt1.textContent).not.toBe(opt2.textContent);
  });

  it('saves via update_with_lines when the draft carries existing_bill_id (routes on existing_bill_id, not matched_account)', async () => {
    setAdmin(true);
    const draft = createMockParsedInvoice({
      existing_bill_id: 7,
      matched_account: createMockBillingAccount({ id: 3 }),
    });
    const { createStub, updateStub } = mountHooks(draft);
    setBillsResponse([createMockBill({ id: 1 })]);

    renderWithProviders(<BillsPage />, { queryClient: createTestQueryClient() });

    await screen.findByRole('button', { name: /importar fatura/i });
    uploadPdf();

    await screen.findByRole('button', { name: /^atualizar$/i });
    await userEvent.click(screen.getByRole('button', { name: /^atualizar$/i }));

    await waitFor(() => {
      expect(updateStub.calls).toHaveLength(1);
    });
    expect(updateStub.calls[0]?.bill_id).toBe(7);
    expect(createStub.calls).toHaveLength(0);
  });

  it('saves via create_with_lines when existing_bill_id is null (even with a matched_account)', async () => {
    setAdmin(true);
    const draft = createMockParsedInvoice({
      existing_bill_id: null,
      matched_account: createMockBillingAccount({ id: 3 }),
    });
    const { createStub, updateStub } = mountHooks(draft);
    setBillsResponse([createMockBill({ id: 1 })]);

    renderWithProviders(<BillsPage />, { queryClient: createTestQueryClient() });

    await screen.findByRole('button', { name: /importar fatura/i });
    uploadPdf();

    await screen.findByRole('button', { name: /^criar$/i });
    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));

    await waitFor(() => {
      expect(createStub.calls).toHaveLength(1);
    });
    expect(updateStub.calls).toHaveLength(0);
  });
});
