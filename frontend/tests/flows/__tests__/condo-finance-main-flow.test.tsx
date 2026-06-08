/**
 * Main condominium-finance flow as an integration test — MSW is the ONLY boundary (no mock of
 * hooks/components/apiClient/TanStack). Real hooks drive the mutation chain and the real
 * Distribution page renders the final read, so the whole data layer is exercised end-to-end:
 *   lançar conta → pagar parcial → mover reserva → fechar mês → projeção → distribuição.
 * Charts are non-blocking, so no SVG is asserted.
 */
import { describe, it, expect } from 'vitest';
import { act, renderHook, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { createTestQueryClient, createWrapper, renderWithProviders } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useCreateBillWithLines, usePayBill } from '@/lib/api/hooks/use-bills';
import { useDepositReserve } from '@/lib/api/hooks/use-reserves';
import { useCloseMonth } from '@/lib/api/hooks/use-condo-month-closes';
import { useCondoProjection } from '@/lib/api/hooks/use-condo-projection';
import DistributionPage from '@/app/(dashboard)/finances/distribution/page';
import {
  createMockBill,
  createMockCondoMonthClose,
  createMockReserve,
} from '@/tests/mocks/data/finances';

const API_BASE = 'http://localhost:8008/api';

describe('condo finance main flow (real hooks + page, MSW boundary)', () => {
  it('runs bill → partial payment → reserve deposit → month close → projection → distribution', async () => {
    const captured: Record<string, unknown> = {};
    server.use(
      http.post(`${API_BASE}/finances/bills/create_with_lines/`, async ({ request }) => {
        captured.createBill = await request.json();
        return HttpResponse.json(createMockBill({ id: 99, description: 'Água' }));
      }),
      http.post(`${API_BASE}/finances/bills/:id/pay/`, async ({ request, params }) => {
        captured.pay = { id: params.id, body: await request.json() };
        // partial payment: still some remaining
        return HttpResponse.json({ id: Number(params.id), payment_status: 'partial', amount_remaining: 100 });
      }),
      http.post(`${API_BASE}/finances/reserves/:id/deposit/`, async ({ request, params }) => {
        captured.deposit = { id: params.id, body: await request.json() };
        return HttpResponse.json(createMockReserve({ id: Number(params.id), balance: 5300 }));
      }),
      http.post(`${API_BASE}/finances/condo-month-closes/close/`, async ({ request }) => {
        captured.close = await request.json();
        return HttpResponse.json(createMockCondoMonthClose({ status: 'closed' }));
      }),
    );

    const client = createTestQueryClient();
    const wrapper = createWrapper(client);

    // 1. Lançar conta (create_with_lines) — capture the lines body.
    const createBill = renderHook(() => useCreateBillWithLines(), { wrapper });
    await act(async () => {
      await createBill.result.current.mutateAsync({
        bill: {
          description: 'Água',
          competence_month: '2026-07-01',
          due_date: '2026-07-10',
          behavior: 'one_time',
        },
        line_items: [{ description: 'Consumo', amount: 300 }],
      });
    });
    expect(captured.createBill).toMatchObject({ line_items: [{ amount: 300 }] });

    // 2. Pagar parcial — amount < total → amount_remaining > 0.
    const pay = renderHook(() => usePayBill(), { wrapper });
    let payRemaining = 0;
    await act(async () => {
      const resp = await pay.result.current.mutateAsync({
        bill_id: 99,
        payment_date: '2026-07-15',
        amount: 200,
      });
      payRemaining = resp.amount_remaining ?? 0;
    });
    expect(captured.pay).toMatchObject({ id: '99', body: { amount: 200 } });
    expect(payRemaining).toBeGreaterThan(0);

    // 3. Mover reserva (deposit) — zero-sum on total balance.
    const deposit = renderHook(() => useDepositReserve(), { wrapper });
    await act(async () => {
      await deposit.result.current.mutateAsync({ reserveId: 1, payload: { amount: 300 } });
    });
    expect(captured.deposit).toMatchObject({ id: '1', body: { amount: 300 } });

    // 4. Fechar mês.
    const close = renderHook(() => useCloseMonth(), { wrapper });
    await act(async () => {
      await close.result.current.mutateAsync({ year: 2026, month: 7 });
    });
    expect(captured.close).toMatchObject({ year: 2026, month: 7 });

    // 5. Projeção (read) — 12 months with mixed is_actual.
    const projection = renderHook(() => useCondoProjection(12), { wrapper });
    await waitFor(() => expect(projection.result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(projection.result.current.data).toHaveLength(12);
    expect(projection.result.current.data?.some((month) => month.is_actual)).toBe(true);

    // 6. Distribuição (render real da página) — household + external owners reflect the backend.
    renderWithProviders(<DistributionPage />, { queryClient: client });
    expect(await screen.findByText('Distribuição por proprietário')).toBeInTheDocument();
    expect(await screen.findByText(/Raul & Célia/)).toBeInTheDocument();
    expect(await screen.findByText('Tiago')).toBeInTheDocument();
    expect(await screen.findByText(/não entra no resultado do condomínio/)).toBeInTheDocument();
  });
});
