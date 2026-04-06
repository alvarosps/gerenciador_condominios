import { z } from 'zod';
import { apartmentSchema } from './apartment.schema';
import { personSimpleSchema } from './credit-card.schema';

export const personIncomeSchema = z.object({
  id: z.number().optional(),
  person: personSimpleSchema.optional(),
  person_id: z.number().optional(),
  income_type: z.string().min(1, 'Tipo é obrigatório'),
  apartment: apartmentSchema.nullable().optional(),
  apartment_id: z.number().nullable().optional(),
  fixed_amount: z
    .string()
    .or(z.number())
    .nullable()
    .optional()
    .transform((val) => (val !== null && val !== undefined ? Number(val) : null)),
  start_date: z.string(),
  end_date: z.string().nullable().optional(),
  is_active: z.boolean().default(true),
  notes: z.string().optional().default(''),
  current_value: z
    .string()
    .or(z.number())
    .optional()
    .transform((val) => (val !== null && val !== undefined ? Number(val) : undefined)),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type PersonIncome = z.infer<typeof personIncomeSchema>;
