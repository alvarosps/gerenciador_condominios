import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useMonthlyCashFlow, useCashFlowProjection } from '../use-cash-flow';
import { useSimulation } from '../use-simulation';
import { createWrapper } from '@/tests/test-utils';

describe('useMonthlyCashFlow', () => {
  it('should fetch monthly data', async () => {
    const { result } = renderHook(() => useMonthlyCashFlow(2026, 3), {
      wrapper: createWrapper(),
    });

    await waitFor(
      () => {
        expect(result.current.isSuccess).toBe(true);
      },
      { timeout: 5000 },
    );

    expect(result.current.data?.year).toBe(2026);
    expect(result.current.data?.month).toBe(3);
    expect(result.current.data?.total_income).toBeDefined();
    expect(result.current.data?.total_expenses).toBeDefined();
    expect(result.current.data?.net_cash_flow).toBeDefined();
  });
});

describe('useCashFlowProjection', () => {
  it('should fetch projection', async () => {
    const { result } = renderHook(() => useCashFlowProjection(3), {
      wrapper: createWrapper(),
    });

    await waitFor(
      () => {
        expect(result.current.isSuccess).toBe(true);
      },
      { timeout: 5000 },
    );

    expect(Array.isArray(result.current.data)).toBe(true);
    expect(result.current.data?.length).toBeGreaterThan(0);
    const firstMonth = result.current.data?.[0];
    expect(firstMonth?.income_total).toBeDefined();
    expect(firstMonth?.expenses_total).toBeDefined();
  });
});

describe('useSimulation', () => {
  it('should send scenarios and return result', async () => {
    const { result } = renderHook(() => useSimulation(), {
      wrapper: createWrapper(),
    });

    result.current.mutate([
      { name: 'Cenário Otimista' },
      { name: 'Cenário Pessimista' },
    ]);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.results).toHaveLength(2);
    const firstResult = result.current.data?.results[0];
    expect(firstResult?.scenario_name).toBe('Cenário Otimista');
    expect(firstResult?.months).toBeDefined();
  });
});
