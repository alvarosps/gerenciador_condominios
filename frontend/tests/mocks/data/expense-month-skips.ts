import type { ExpenseMonthSkip } from '@/lib/schemas/expense-month-skip.schema';

export const mockExpenseMonthSkips: ExpenseMonthSkip[] = [
  {
    id: 1,
    expense_id: 1,
    expense_description: 'Aluguel escritório',
    reference_month: '2026-03-01',
    created_at: '2026-03-01T00:00:00Z',
    updated_at: '2026-03-01T00:00:00Z',
  },
];

let nextId = 100;

export function createMockExpenseMonthSkip(
  overrides?: Partial<ExpenseMonthSkip>,
): ExpenseMonthSkip {
  return {
    id: nextId++,
    expense_id: 1,
    expense_description: 'Some expense',
    reference_month: '2026-03-01',
    created_at: '2026-03-01T00:00:00Z',
    updated_at: '2026-03-01T00:00:00Z',
    ...overrides,
  };
}
