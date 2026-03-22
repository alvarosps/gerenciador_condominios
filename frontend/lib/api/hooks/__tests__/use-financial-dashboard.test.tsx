import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useFinancialOverview, useDebtByPerson, useUpcomingInstallments } from '../use-financial-dashboard';
import { createWrapper } from '@/tests/test-utils';

describe('useFinancialOverview', () => {
  it('should fetch overview', async () => {
    const { result } = renderHook(() => useFinancialOverview(), {
      wrapper: createWrapper(),
    });

    await waitFor(
      () => {
        expect(result.current.isSuccess).toBe(true);
      },
      { timeout: 5000 },
    );

    expect(result.current.data?.total_expenses).toBeDefined();
    expect(result.current.data?.total_income).toBeDefined();
    expect(result.current.data?.net_balance).toBeDefined();
  });
});

describe('useDebtByPerson', () => {
  it('should fetch debt by person', async () => {
    const { result } = renderHook(() => useDebtByPerson(), {
      wrapper: createWrapper(),
    });

    await waitFor(
      () => {
        expect(result.current.isSuccess).toBe(true);
      },
      { timeout: 5000 },
    );

    expect(Array.isArray(result.current.data)).toBe(true);
    const firstEntry = result.current.data?.[0];
    expect(firstEntry?.person_name).toBeDefined();
    expect(firstEntry?.total_debt).toBeDefined();
  });
});

describe('useUpcomingInstallments', () => {
  it('should fetch with custom days', async () => {
    const { result } = renderHook(() => useUpcomingInstallments(30), {
      wrapper: createWrapper(),
    });

    await waitFor(
      () => {
        expect(result.current.isSuccess).toBe(true);
      },
      { timeout: 5000 },
    );

    expect(Array.isArray(result.current.data)).toBe(true);
  });
});
