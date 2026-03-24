import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import {
  useFinancialOverview,
  useDebtByPerson,
  useDebtByType,
  useUpcomingInstallments,
  useOverdueInstallments,
  useCategoryBreakdown,
  useDashboardSummary,
  useExpenseDetail,
} from '../use-financial-dashboard';
import { createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8000/api';

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

    expect(result.current.data?.current_month_expenses).toBeDefined();
    expect(result.current.data?.current_month_income).toBeDefined();
    expect(result.current.data?.current_month_balance).toBeDefined();
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

describe('useDebtByType', () => {
  it('should fetch debt by type', async () => {
    const { result } = renderHook(() => useDebtByType(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(result.current.data).toBeDefined();
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

  it('should fetch without days parameter', async () => {
    const { result } = renderHook(() => useUpcomingInstallments(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(Array.isArray(result.current.data)).toBe(true);
  });

  it('should convert amount to number', async () => {
    const { result } = renderHook(() => useUpcomingInstallments(30), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    result.current.data?.forEach((installment) => {
      expect(typeof installment.amount).toBe('number');
    });
  });
});

describe('useOverdueInstallments', () => {
  it('should fetch overdue installments', async () => {
    const { result } = renderHook(() => useOverdueInstallments(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(Array.isArray(result.current.data)).toBe(true);
  });

  it('should handle error from server', async () => {
    server.use(
      http.get(`${API_BASE}/financial-dashboard/overdue_installments/`, () => {
        return new HttpResponse(null, { status: 500 });
      }),
    );

    const { result } = renderHook(() => useOverdueInstallments(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});

describe('useCategoryBreakdown', () => {
  it('should fetch category breakdown for given year and month', async () => {
    const { result } = renderHook(() => useCategoryBreakdown(2026, 3), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(Array.isArray(result.current.data)).toBe(true);
    expect(result.current.data?.length).toBeGreaterThan(0);
    const firstCategory = result.current.data?.[0];
    expect(firstCategory?.category_name).toBeDefined();
    expect(firstCategory?.total).toBeDefined();
    expect(firstCategory?.percentage).toBeDefined();
  });
});

describe('useDashboardSummary', () => {
  it('should not fetch when server returns error', async () => {
    server.use(
      http.get(`${API_BASE}/financial-dashboard/dashboard_summary/`, () => {
        return new HttpResponse(null, { status: 500 });
      }),
    );

    const { result } = renderHook(() => useDashboardSummary(2026, 3), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });

  it('should fetch dashboard summary for given year and month', async () => {
    server.use(
      http.get(`${API_BASE}/financial-dashboard/dashboard_summary/`, () => {
        return HttpResponse.json({
          year: 2026,
          month: 3,
          overdue_items: [],
          income_summary: {
            total_monthly_income: 12000,
            all_apartments: [],
            owner_incomes: [],
            owner_total: 0,
            vacant_kitnets: [],
            vacant_by_building: [],
            vacant_count: 0,
            vacant_lost_rent: 0,
            condominium_income: 10000,
            condominium_kitnet_count: 8,
            extra_incomes: [],
            extra_income_total: 2000,
          },
          expense_summary: {
            by_person: [],
            water: { total: 0, by_building: [] },
            electricity: { total: 0, by_building: [] },
            iptu: { total: 0, by_building: [] },
            internet: { total: 0, details: [] },
            celular: { total: 0, details: [] },
            sitio: { total: 0, details: [] },
            outros_fixed: { total: 0, details: [] },
            employee: { total: 0, details: [] },
            total: 5200,
          },
          overdue_total: 0,
          monthly_expenses: 5200,
          current_month_income: 12000,
          current_month_expenses: 5200,
          current_month_balance: 6800,
        });
      }),
    );

    const { result } = renderHook(() => useDashboardSummary(2026, 3), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(result.current.data?.year).toBe(2026);
    expect(result.current.data?.month).toBe(3);
    expect(result.current.data?.current_month_balance).toBe(6800);
  });
});

describe('useExpenseDetail', () => {
  it('should not fetch when type is empty string', () => {
    const { result } = renderHook(() => useExpenseDetail('', null, 2026, 3), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBeUndefined();
  });

  it('should fetch expense detail when type is provided', async () => {
    server.use(
      http.get(`${API_BASE}/financial-dashboard/expense_detail/`, () => {
        return HttpResponse.json({
          detail_type: 'person',
          person_id: 1,
          person_name: 'Rodrigo Souza',
          total: 800,
          total_paid: 500,
          pending: 300,
          is_payable: true,
        });
      }),
    );

    const { result } = renderHook(() => useExpenseDetail('person', 1, 2026, 3), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(result.current.data?.detail_type).toBe('person');
  });
});
