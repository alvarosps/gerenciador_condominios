import { z } from 'zod';

export const expenseMonthSkipSchema = z.object({
  id: z.number().optional(),
  expense_id: z.number().optional(),
  expense_description: z.string().optional(),
  reference_month: z.string(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type ExpenseMonthSkip = z.infer<typeof expenseMonthSkipSchema>;
