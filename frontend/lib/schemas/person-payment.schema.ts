import { z } from 'zod';
import { personSimpleSchema } from './credit-card.schema';

export const personPaymentSchema = z.object({
  id: z.number().optional(),
  person: personSimpleSchema.optional(),
  person_id: z.number().optional(),
  reference_month: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Formato inválido (YYYY-MM-DD)'),
  amount: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  payment_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Formato inválido (YYYY-MM-DD)'),
  notes: z.string().optional().default(''),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type PersonPayment = z.infer<typeof personPaymentSchema>;
