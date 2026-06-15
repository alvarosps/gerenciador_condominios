import { describe, it, expect, beforeAll, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import {
  createMockBill,
  createMockBillingAccount,
  createMockParsedInvoice,
} from '@/tests/mocks/data/finances';
import BillsPage from '../page';
import { type z } from 'zod';
import { billingAccountSchema } from '@/lib/schemas/finances/billing-account.schema';
import { type parsedInvoiceSchema } from '@/lib/schemas/finances/invoice-parse.schema';

// Real hooks (useParseInvoice / useCreateBillWithLines / useUpdateBillWithLines / …) hit MSW. The
// parse → create/update flow is exercised end-to-end; each mutation is spied via an MSW
// request-body capture (the point: it exercises the form's real write serialization).
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
  server.use(http.get(`${API_BASE}/finances/billing-accounts/`, () => HttpResponse.json(accounts)));
}

function setIptuAlerts() {
  server.use(
    http.get(`${API_BASE}/finances/finance-dashboard/iptu_alerts/`, () =>
      HttpResponse.json({ alerts: [], warning_count: 0, critical_count: 0 })
    )
  );
}

function setAdmin(isStaff: boolean) {
  useAuthStore.setState({
    user: { id: 1, email: 'a@b.c', first_name: 'A', last_name: 'B', is_staff: isStaff },
    isAuthenticated: true,
  });
}

interface CreateBody {
  bill: Record<string, unknown>;
  line_items: unknown[];
  statement: unknown;
}

interface UpdateBody {
  bill: Record<string, unknown>;
  line_items: unknown[];
  statement: unknown;
}

// Make parse_invoice resolve to a specific draft so the modal opens prefilled from it.
function setParseInvoice(draft: z.input<typeof parsedInvoiceSchema>) {
  server.use(
    http.post(`${API_BASE}/finances/bills/parse_invoice/`, () => HttpResponse.json(draft))
  );
}

// Spy create_with_lines via an MSW request-body capture.
function spyCreateWithLines() {
  const bodies: CreateBody[] = [];
  server.use(
    http.post(`${API_BASE}/finances/bills/create_with_lines/`, async ({ request }) => {
      bodies.push((await request.json()) as CreateBody);
      return HttpResponse.json(createMockBill({ id: 99 }), { status: 201 });
    })
  );
  return bodies;
}

// Spy update_with_lines via an MSW request-body capture (captures the path :id too).
function spyUpdateWithLines() {
  const bodies: (UpdateBody & { bill_id: number })[] = [];
  server.use(
    http.post(`${API_BASE}/finances/bills/:id/update_with_lines/`, async ({ params, request }) => {
      const body = (await request.json()) as UpdateBody;
      bodies.push({ ...body, bill_id: Number(params.id) });
      return HttpResponse.json(createMockBill({ id: Number(params.id) }));
    })
  );
  return bodies;
}

function uploadPdf() {
  const input = document.querySelector<HTMLInputElement>('input[type="file"]');
  if (!input) throw new Error('file input not found');
  const file = new File(['%PDF'], 'fatura.pdf', { type: 'application/pdf' });
  fireEvent.change(input, { target: { files: [file] } });
}

describe('BillsPage — import fatura + disambiguated accounts', () => {
  beforeEach(() => {
    setIptuAlerts();
    setBillingAccounts([]);
  });

  it('hides "Importar fatura" and "Nova Conta" for non-admin users', async () => {
    setAdmin(false);
    setBillsResponse([createMockBill({ id: 1, description: 'Conta de Luz' })]);

    const { queryClient } = renderWithProviders(<BillsPage />);

    expect((await screen.findAllByText('Conta de Luz')).length).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: /importar fatura/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /nova conta/i })).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('shows "Importar fatura" for admin users', async () => {
    setAdmin(true);
    setBillsResponse([createMockBill({ id: 1, description: 'Conta de Luz' })]);

    const { queryClient } = renderWithProviders(<BillsPage />);

    expect(await screen.findByRole('button', { name: /importar fatura/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /nova conta/i })).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
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
        {
          description: 'Consumo de água',
          amount: 80,
          is_offset: false,
          category_id: null,
          installment_id: null,
        },
        {
          description: 'PARCELA 3/59',
          amount: 12,
          is_offset: false,
          category_id: null,
          installment_id: 42,
        },
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
    setParseInvoice(draft);
    setBillsResponse([createMockBill({ id: 1, description: 'Conta de Luz' })]);

    const { queryClient } = renderWithProviders(<BillsPage />);

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

    await waitForQueriesToSettle(queryClient);
  });

  it('renders two same-type accounts with distinct disambiguated labels "name — tipo · external_identifier"', async () => {
    setAdmin(true);
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

    const { queryClient } = renderWithProviders(<BillsPage />);

    const user = userEvent.setup({ pointerEventsCheck: 0 });
    await user.click(await screen.findByRole('button', { name: /nova conta/i }));
    // Switch to recurring to reveal the billing-account select.
    await user.click(await screen.findByLabelText('Tipo'));
    await user.click(await screen.findByRole('option', { name: 'Recorrente' }));
    await user.click(await screen.findByText('Conta recorrente'));

    const opt1 = await screen.findByRole('option', {
      name: /Conta de Luz - 836 — Luz · 1\.273\.798\.010-05/,
    });
    const opt2 = await screen.findByRole('option', {
      name: /Conta de Luz - 850 — Luz · 9\.999\.999\.999-99/,
    });
    expect(opt1).toBeInTheDocument();
    expect(opt2).toBeInTheDocument();
    expect(opt1.textContent).not.toBe(opt2.textContent);

    await waitForQueriesToSettle(queryClient);
  });

  it('saves via update_with_lines when the draft carries existing_bill_id (routes on existing_bill_id, not matched_account)', async () => {
    setAdmin(true);
    const draft = createMockParsedInvoice({
      existing_bill_id: 7,
      matched_account: billingAccountSchema.parse(createMockBillingAccount({ id: 3 })),
    });
    setParseInvoice(draft);
    const createBodies = spyCreateWithLines();
    const updateBodies = spyUpdateWithLines();
    setBillsResponse([createMockBill({ id: 1 })]);

    const { queryClient } = renderWithProviders(<BillsPage />);

    await screen.findByRole('button', { name: /importar fatura/i });
    uploadPdf();

    await screen.findByRole('button', { name: /^atualizar$/i });
    await userEvent.click(screen.getByRole('button', { name: /^atualizar$/i }));

    await waitFor(() => {
      expect(updateBodies).toHaveLength(1);
    });
    expect(updateBodies[0]?.bill_id).toBe(7);
    expect(createBodies).toHaveLength(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('saves via create_with_lines when existing_bill_id is null (even with a matched_account)', async () => {
    setAdmin(true);
    const draft = createMockParsedInvoice({
      existing_bill_id: null,
      matched_account: billingAccountSchema.parse(createMockBillingAccount({ id: 3 })),
    });
    setParseInvoice(draft);
    const createBodies = spyCreateWithLines();
    const updateBodies = spyUpdateWithLines();
    setBillsResponse([createMockBill({ id: 1 })]);

    const { queryClient } = renderWithProviders(<BillsPage />);

    await screen.findByRole('button', { name: /importar fatura/i });
    uploadPdf();

    await screen.findByRole('button', { name: /^criar$/i });
    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));

    await waitFor(() => {
      expect(createBodies).toHaveLength(1);
    });
    expect(updateBodies).toHaveLength(0);

    await waitForQueriesToSettle(queryClient);
  });
});
