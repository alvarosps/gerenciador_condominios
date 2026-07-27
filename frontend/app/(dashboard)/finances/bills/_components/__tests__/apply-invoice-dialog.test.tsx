import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockBill, createMockParsedInvoice } from '@/tests/mocks/data/finances';
import { ApplyInvoiceDialog } from '../apply-invoice-dialog';
import { billSchema, type Bill } from '@/lib/schemas/finances/bill.schema';
import {
  parsedInvoiceSchema,
  type ParsedInvoice,
} from '@/lib/schemas/finances/invoice-parse.schema';

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

function spyApplyInvoice() {
  const calls: { bill_id: number }[] = [];
  server.use(
    http.post(`${API_BASE}/finances/bills/:id/apply_invoice/`, ({ params }) => {
      calls.push({ bill_id: Number(params.id) });
      return HttpResponse.json(
        createMockBill({ id: Number(params.id), amount_is_estimated: false })
      );
    })
  );
  return calls;
}

function targetBill(): Bill {
  return billSchema.parse(
    createMockBill({
      id: 7,
      billing_account: {
        id: 3,
        name: 'Água 836',
        account_type: 'water',
        external_identifier: 'UC-1',
        default_due_day: 10,
        expected_amount: '0.00',
        lifecycle_state: 'active',
      },
      amount_is_estimated: true,
    })
  );
}

function pdfFile(): File {
  return new File(['%PDF'], 'fatura.pdf', { type: 'application/pdf' });
}

function draft(overrides: Parameters<typeof createMockParsedInvoice>[0] = {}): ParsedInvoice {
  return parsedInvoiceSchema.parse(createMockParsedInvoice(overrides));
}

describe('ApplyInvoiceDialog', () => {
  beforeEach(() => {
    vi.mocked(toast.success).mockReset();
    vi.mocked(toast.error).mockReset();
  });

  it('shows draft warnings in an Alert before any apply request is made', async () => {
    const calls = spyApplyInvoice();
    const invoiceDraft = draft({
      matched_account: {
        id: 3,
        name: 'Água 836',
        account_type: 'water',
        external_identifier: 'UC-1',
        default_due_day: 10,
        expected_amount: '0.00',
        lifecycle_state: 'active',
      },
      warnings: ['Valor de parcela divergente não aplicado'],
    });

    renderWithProviders(
      <ApplyInvoiceDialog
        open
        bill={targetBill()}
        draft={invoiceDraft}
        file={pdfFile()}
        onClose={vi.fn()}
      />
    );

    expect(
      await screen.findByText(/valor de parcela divergente não aplicado/i)
    ).toBeInTheDocument();
    expect(calls).toHaveLength(0);
  });

  it('blocks confirmation when the matched account diverges from the bill account', async () => {
    const calls = spyApplyInvoice();
    const invoiceDraft = draft({
      matched_account: {
        id: 999, // diverges from the bill's billing_account.id (3)
        name: 'Água 850',
        account_type: 'water',
        external_identifier: 'UC-2',
        default_due_day: 10,
        expected_amount: '0.00',
        lifecycle_state: 'active',
      },
    });

    renderWithProviders(
      <ApplyInvoiceDialog
        open
        bill={targetBill()}
        draft={invoiceDraft}
        file={pdfFile()}
        onClose={vi.fn()}
      />
    );

    expect(await screen.findByText(/conta divergente/i)).toBeInTheDocument();
    const confirmButton = screen.getByRole('button', { name: /confirmar/i });
    expect(confirmButton).toBeDisabled();

    await userEvent.click(confirmButton).catch(() => undefined);
    expect(calls).toHaveLength(0);
  });

  it('posts the file to bills/{id}/apply_invoice/ only after explicit confirmation', async () => {
    const calls = spyApplyInvoice();
    const invoiceDraft = draft({
      matched_account: {
        id: 3,
        name: 'Água 836',
        account_type: 'water',
        external_identifier: 'UC-1',
        default_due_day: 10,
        expected_amount: '0.00',
        lifecycle_state: 'active',
      },
    });

    const { queryClient } = renderWithProviders(
      <ApplyInvoiceDialog
        open
        bill={targetBill()}
        draft={invoiceDraft}
        file={pdfFile()}
        onClose={vi.fn()}
      />
    );

    await screen.findByRole('button', { name: /confirmar/i });
    expect(calls).toHaveLength(0);

    await userEvent.click(screen.getByRole('button', { name: /confirmar/i }));

    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]?.bill_id).toBe(7);

    await waitForQueriesToSettle(queryClient);
  });

  it('surfaces the backend 400 (competência divergente / mês fechado) as a PT toast', async () => {
    server.use(
      http.post(`${API_BASE}/finances/bills/7/apply_invoice/`, () =>
        HttpResponse.json({ detail: 'Competência 06/2026 está fechada.' }, { status: 400 })
      )
    );
    const invoiceDraft = draft({
      matched_account: {
        id: 3,
        name: 'Água 836',
        account_type: 'water',
        external_identifier: 'UC-1',
        default_due_day: 10,
        expected_amount: '0.00',
        lifecycle_state: 'active',
      },
    });

    const { queryClient } = renderWithProviders(
      <ApplyInvoiceDialog
        open
        bill={targetBill()}
        draft={invoiceDraft}
        file={pdfFile()}
        onClose={vi.fn()}
      />
    );

    await userEvent.click(await screen.findByRole('button', { name: /confirmar/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Competência 06/2026 está fechada.');
    });

    await waitForQueriesToSettle(queryClient);
  });
});
