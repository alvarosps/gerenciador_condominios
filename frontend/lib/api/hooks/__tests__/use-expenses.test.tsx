import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useExpenses, useCreateExpense, useMarkExpensePaid, useGenerateInstallments } from '../use-expenses';
import { useMarkInstallmentPaid, useBulkMarkInstallmentsPaid } from '../use-expense-installments';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { mockExpenses } from '@/tests/mocks/data';

describe('useExpenses', () => {
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
