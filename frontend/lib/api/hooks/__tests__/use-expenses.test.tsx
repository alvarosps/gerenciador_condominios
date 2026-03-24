import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import {
  useExpenses,
  useExpense,
  useCreateExpense,
  useUpdateExpense,
  useDeleteExpense,
  useMarkExpensePaid,
  useGenerateInstallments,
} from '../use-expenses';
import { useMarkInstallmentPaid, useBulkMarkInstallmentsPaid } from '../use-expense-installments';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { mockExpenses } from '@/tests/mocks/data';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8000/api';

describe('useExpenses', () => {
  it('should fetch all expenses without filters', async () => {
    const { result } = renderHook(() => useExpenses(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(result.current.data).toBeDefined();
    expect(Array.isArray(result.current.data)).toBe(true);
  });

  it('should handle server error', async () => {
    server.use(
      http.get(`${API_BASE}/expenses/`, () => {
        return new HttpResponse(null, { status: 500 });
      }),
    );

    const { result } = renderHook(() => useExpenses({ is_offset: true }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });

  it('should fetch expenses with filters', async () => {
    const { result } = renderHook(() => useExpenses({ expense_type: 'card_purchase' }), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(
      () => {
        expect(result.current.isSuccess).toBe(true);
      },
      { timeout: 5000 },
    );

    expect(result.current.data).toBeDefined();
    expect(Array.isArray(result.current.data)).toBe(true);
  });

  it('should create expense', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useCreateExpense(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({
      description: 'Nova despesa',
      expense_type: 'fixed_expense',
      total_amount: 200.0,
      expense_date: '2026-03-22',
      is_installment: false,
      is_debt_installment: false,
      is_offset: false,
      is_recurring: false,
      expected_monthly_amount: null,
      is_paid: false,
      bank_name: '',
      interest_rate: null,
      notes: '',
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['expenses'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['financial-dashboard'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
  });

  it('should mark expense as paid', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useMarkExpensePaid(), {
      wrapper: createWrapper(queryClient),
    });

    const firstExpense = mockExpenses[0];
    if (!firstExpense?.id) throw new Error('Test data missing');

    result.current.mutate(firstExpense.id);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['expenses'] });
  });

  it('should generate installments', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useGenerateInstallments(), {
      wrapper: createWrapper(queryClient),
    });

    const firstExpense = mockExpenses[0];
    if (!firstExpense?.id) throw new Error('Test data missing');

    result.current.mutate(firstExpense.id);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.message).toBeDefined();
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['expense-installments'] });
  });
});

describe('useExpense (single)', () => {
  it('should fetch a single expense by ID', async () => {
    const firstExpense = mockExpenses[0];
    if (!firstExpense?.id) throw new Error('Test data missing');

    const { result } = renderHook(() => useExpense(firstExpense.id ?? null), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(result.current.data?.id).toBe(firstExpense.id);
  });

  it('should not fetch when ID is null', () => {
    const { result } = renderHook(() => useExpense(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBeUndefined();
  });

  it('should handle 404 for non-existent expense', async () => {
    const { result } = renderHook(() => useExpense(9999), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});

describe('useUpdateExpense', () => {
  it('should update an expense and invalidate caches', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const firstExpense = mockExpenses[0];
    if (!firstExpense?.id) throw new Error('Test data missing');

    const { result } = renderHook(() => useUpdateExpense(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({
      id: firstExpense.id,
      description: 'Despesa atualizada',
      expense_type: firstExpense.expense_type,
      total_amount: 300,
      expense_date: firstExpense.expense_date,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['expenses'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['financial-dashboard'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
  });
});

describe('useDeleteExpense', () => {
  it('should delete an expense and invalidate caches', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useDeleteExpense(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate(1);

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['expenses'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['financial-dashboard'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
  });
});

describe('useExpenseInstallments', () => {
  it('should mark installment as paid', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useMarkInstallmentPaid(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate(1);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['expense-installments'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['expenses'] });
  });

  it('should bulk mark installments as paid', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useBulkMarkInstallmentsPaid(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate([1, 2, 3]);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.updated_count).toBe(3);
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['expense-installments'] });
  });
});
