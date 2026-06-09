import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import {
  useCreateBillWithLines,
  useParseInvoice,
  useUpdateBillWithLines,
} from '../use-bills';
import { createTestQueryClient, createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockBill, createMockParsedInvoice } from '@/tests/mocks/data/finances';

const API_BASE = 'http://localhost:8008/api';

function pdfFile(): File {
  return new File(['%PDF-1.4 fake'], 'fatura.pdf', { type: 'application/pdf' });
}

describe('useParseInvoice', () => {
  it('posts FormData with a multipart Content-Type override and returns the parsed draft', async () => {
    let capturedContentType = '';
    let capturedHadFile = false;
    server.use(
      http.post(`${API_BASE}/finances/bills/parse_invoice/`, async ({ request }) => {
        capturedContentType = request.headers.get('content-type') ?? '';
        const form = await request.formData();
        capturedHadFile = form.get('file') instanceof File;
        return HttpResponse.json(
          createMockParsedInvoice({ existing_bill_id: null, warnings: ['aviso'] }),
        );
      }),
    );

    const { result } = renderHook(() => useParseInvoice(), { wrapper: createWrapper() });
    result.current.mutate(pdfFile());

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(capturedContentType.startsWith('multipart/form-data')).toBe(true);
    expect(capturedHadFile).toBe(true);
    // The draft is a single object (not {results,count}) — returned raw, not unwrapped.
    expect(result.current.data?.bill.description).toBe('Conta de Luz - Prédio 836');
    expect(result.current.data?.line_items.length).toBeGreaterThan(0);
    expect(result.current.data?.warnings).toEqual(['aviso']);
  });

  it('does NOT invalidate caches (parse_invoice never writes)', async () => {
    server.use(
      http.post(`${API_BASE}/finances/bills/parse_invoice/`, () =>
        HttpResponse.json(createMockParsedInvoice()),
      ),
    );
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useParseInvoice(), {
      wrapper: createWrapper(queryClient),
    });
    result.current.mutate(pdfFile());

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(invalidateSpy).not.toHaveBeenCalled();
  });

  it('surfaces a 400/422 error to the caller (não-PDF / emissor desconhecido)', async () => {
    server.use(
      http.post(`${API_BASE}/finances/bills/parse_invoice/`, () =>
        HttpResponse.json({ error: 'O arquivo enviado não é um PDF válido.' }, { status: 400 }),
      ),
    );

    const { result } = renderHook(() => useParseInvoice(), { wrapper: createWrapper() });
    result.current.mutate(pdfFile());

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});

describe('useUpdateBillWithLines', () => {
  it('posts to bills/{id}/update_with_lines and invalidates bill caches', async () => {
    let capturedUrl = '';
    let capturedBody: Record<string, unknown> = {};
    server.use(
      http.post(`${API_BASE}/finances/bills/:id/update_with_lines/`, async ({ request }) => {
        capturedUrl = request.url;
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(createMockBill({ id: 7, description: 'Atualizada' }));
      }),
    );

    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const { result } = renderHook(() => useUpdateBillWithLines(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({
      bill_id: 7,
      bill: { description: 'Atualizada' },
      line_items: [{ description: 'Água', amount: 120 }],
      statement: null,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(capturedUrl).toContain('/finances/bills/7/update_with_lines/');
    expect(capturedBody.line_items).toBeInstanceOf(Array);
    expect(result.current.data?.id).toBe(7);
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'bills'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'combined-calendar'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'overdue-bills'] });
  });
});

describe('useCreateBillWithLines', () => {
  it('forwards the optional statement in the payload', async () => {
    let capturedBody: Record<string, unknown> = {};
    server.use(
      http.post(`${API_BASE}/finances/bills/create_with_lines/`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(createMockBill({ id: 9 }), { status: 201 });
      }),
    );

    const { result } = renderHook(() => useCreateBillWithLines(), { wrapper: createWrapper() });

    result.current.mutate({
      bill: { description: 'Água', behavior: 'recurring' },
      line_items: [{ description: 'Consumo', amount: 80 }],
      statement: { kind: 'water', consumo_m3: 12 },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(capturedBody.statement).toMatchObject({ kind: 'water', consumo_m3: 12 });
  });
});
