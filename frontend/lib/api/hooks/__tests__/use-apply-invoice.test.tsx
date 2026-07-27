import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useApplyInvoice } from '../use-bills';
import { createTestQueryClient, createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockBill } from '@/tests/mocks/data/finances';

const API_BASE = 'http://localhost:8008/api';

function pdfFile(): File {
  return new File(['%PDF-1.4 fake'], 'fatura.pdf', { type: 'application/pdf' });
}

describe('useApplyInvoice', () => {
  it('posts multipart FormData to bills/{id}/apply_invoice/ and returns the parsed bill', async () => {
    let capturedContentType = '';
    let capturedHadFile = false;
    server.use(
      http.post(`${API_BASE}/finances/bills/42/apply_invoice/`, async ({ request }) => {
        capturedContentType = request.headers.get('content-type') ?? '';
        const form = await request.formData();
        capturedHadFile = form.get('file') instanceof File;
        return HttpResponse.json(createMockBill({ id: 42, amount_is_estimated: false }));
      })
    );

    const { result } = renderHook(() => useApplyInvoice(), { wrapper: createWrapper() });
    result.current.mutate({ bill_id: 42, file: pdfFile() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(capturedContentType.startsWith('multipart/form-data')).toBe(true);
    expect(capturedHadFile).toBe(true);
    expect(result.current.data?.id).toBe(42);
    expect(result.current.data?.amount_is_estimated).toBe(false);
  });

  it('invalidates bills + monthBoard + billingAccounts + money caches on success (apply WRITES)', async () => {
    server.use(
      http.post(`${API_BASE}/finances/bills/42/apply_invoice/`, () =>
        HttpResponse.json(createMockBill({ id: 42 }))
      )
    );

    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const { result } = renderHook(() => useApplyInvoice(), { wrapper: createWrapper(queryClient) });

    result.current.mutate({ bill_id: 42, file: pdfFile() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'bills'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'combined-calendar'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'overdue-bills'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'month-board'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'billing-accounts'] });
  });

  it('propagates a 400 mismatch/closed-month error to the caller (PT backend message)', async () => {
    server.use(
      http.post(`${API_BASE}/finances/bills/42/apply_invoice/`, () =>
        HttpResponse.json(
          { detail: 'A competência da fatura não corresponde à da conta.' },
          { status: 400 }
        )
      )
    );

    const { result } = renderHook(() => useApplyInvoice(), { wrapper: createWrapper() });
    result.current.mutate({ bill_id: 42, file: pdfFile() });

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});
