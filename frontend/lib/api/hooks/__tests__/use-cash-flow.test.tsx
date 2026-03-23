import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useMonthlyCashFlow, useCashFlowProjection } from '../use-cash-flow';
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
    expect(result.current.data?.income.total).toBe(12000.0);
    expect(result.current.data?.expenses.total).toBe(5200.0);
    expect(result.current.data?.balance).toBe(6800.0);
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
