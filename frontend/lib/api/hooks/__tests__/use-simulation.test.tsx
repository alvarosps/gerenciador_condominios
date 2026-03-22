import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { server } from '@/tests/mocks/server';
import { http, HttpResponse } from 'msw';
import { useSimulation } from '../use-simulation';
import { createWrapper } from '@/tests/test-utils';

const API_BASE = 'http://localhost:8000/api';

describe('useSimulation', () => {
  it('sends scenarios and returns comparison result', async () => {
    const { result } = renderHook(() => useSimulation(), {
      wrapper: createWrapper(),
    });

    result.current.mutate([{ type: 'add_fixed_expense', amount: 500 }]);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.base).toBeDefined();
    expect(result.current.data?.simulated).toBeDefined();
    expect(result.current.data?.comparison).toBeDefined();
    expect(result.current.data?.comparison.month_by_month.length).toBeGreaterThan(0);
    expect(result.current.data?.comparison.total_impact_12m).toBeDefined();
  });

  it('handles empty scenarios with API error', async () => {
    server.use(
      http.post(`${API_BASE}/cash-flow/simulate/`, () => {
        return HttpResponse.json(
          { error: "O campo 'scenarios' é obrigatório e deve ser uma lista não vazia." },
          { status: 400 },
        );
      }),
    );

    const { result } = renderHook(() => useSimulation(), {
      wrapper: createWrapper(),
    });

    result.current.mutate([]);

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it('handles API error gracefully', async () => {
    server.use(
      http.post(`${API_BASE}/cash-flow/simulate/`, () => {
        return HttpResponse.json(
          { error: 'Internal server error' },
          { status: 500 },
        );
      }),
    );

    const { result } = renderHook(() => useSimulation(), {
      wrapper: createWrapper(),
    });

    result.current.mutate([{ type: 'pay_off_early', expense_id: 999 }]);

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.data).toBeUndefined();
  });
});
