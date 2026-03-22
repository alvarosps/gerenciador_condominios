import { z } from 'zod';
import { buildingSchema } from './building.schema';
import { personSimpleSchema } from './credit-card.schema';
import { expenseCategorySchema } from './expense-category.schema';

export const incomeSchema = z.object({
  id: z.number().optional(),
  description: z.string().min(1, 'Descrição é obrigatória'),
  amount: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  income_date: z.string(),
  person: personSimpleSchema.nullable().optional(),
  person_id: z.number().nullable().optional(),
  building: buildingSchema.nullable().optional(),
  building_id: z.number().nullable().optional(),
  category: expenseCategorySchema.nullable().optional(),
  category_id: z.number().nullable().optional(),
  is_recurring: z.boolean().default(false),
  expected_monthly_amount: z
    .string()
    .or(z.number())
    .nullable()
    .optional()
    .transform((val) => (val !== null && val !== undefined ? Number(val) : null)),
  is_received: z.boolean().default(false),
  received_date: z.string().nullable().optional(),
  notes: z.string().optional().default(''),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type Income = z.infer<typeof incomeSchema>;
