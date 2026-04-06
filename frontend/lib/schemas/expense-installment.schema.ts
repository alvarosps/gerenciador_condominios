import { z } from 'zod';

export const expenseInstallmentSchema = z.object({
  id: z.number().optional(),
  expense: z.number(),
  installment_number: z.number(),
  total_installments: z.number(),
  amount: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  due_date: z.string(),
  is_paid: z.boolean().default(false),
  paid_date: z.string().nullable().optional(),
  notes: z.string().optional().default(''),
  is_overdue: z.boolean().optional(),
});

export type ExpenseInstallment = z.infer<typeof expenseInstallmentSchema>;
