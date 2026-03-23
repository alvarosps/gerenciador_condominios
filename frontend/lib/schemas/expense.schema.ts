import { z } from 'zod';
import { buildingSchema } from './building.schema';
import { personSimpleSchema } from './credit-card.schema';
import { creditCardSchema } from './credit-card.schema';
import { expenseCategorySchema } from './expense-category.schema';
import { expenseInstallmentSchema } from './expense-installment.schema';

export const expenseSchema = z.object({
  id: z.number().optional(),
  description: z.string().min(1, 'Descrição é obrigatória'),
  expense_type: z.string().min(1, 'Tipo é obrigatório'),
  total_amount: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  expense_date: z.string(),
  person: personSimpleSchema.nullable().optional(),
  person_id: z.number().nullable().optional(),
  credit_card: creditCardSchema.nullable().optional(),
  credit_card_id: z.number().nullable().optional(),
  building: buildingSchema.nullable().optional(),
  building_id: z.number().nullable().optional(),
  category: expenseCategorySchema.nullable().optional(),
  category_id: z.number().nullable().optional(),
  is_installment: z.boolean().default(false),
  total_installments: z.number().nullable().optional(),
  is_debt_installment: z.boolean().default(false),
  is_offset: z.boolean().default(false),
  is_recurring: z.boolean().default(false),
  expected_monthly_amount: z
    .string()
    .or(z.number())
    .nullable()
    .optional()
    .transform((val) => (val !== null && val !== undefined ? Number(val) : null)),
  recurrence_day: z.number().nullable().optional(),
  is_paid: z.boolean().default(false),
  paid_date: z.string().nullable().optional(),
  bank_name: z.string().optional().default(''),
  interest_rate: z
    .string()
    .or(z.number())
    .nullable()
    .optional()
    .transform((val) => (val !== null && val !== undefined ? Number(val) : null)),
  notes: z.string().optional().default(''),
  installments: z.array(expenseInstallmentSchema).default([]),
  remaining_installments: z.number().optional(),
  total_paid: z
    .string()
    .or(z.number())
    .optional()
    .transform((val) => (val !== null && val !== undefined ? Number(val) : undefined)),
  total_remaining: z
    .string()
    .or(z.number())
    .optional()
    .transform((val) => (val !== null && val !== undefined ? Number(val) : undefined)),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type Expense = z.infer<typeof expenseSchema>;
