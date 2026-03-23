import { z } from 'zod';
import { personSimpleSchema } from './credit-card.schema';

export const personPaymentSchema = z.object({
  id: z.number().optional(),
  person: personSimpleSchema.optional(),
  person_id: z.number().optional(),
  reference_month: z.string(),
  amount: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  payment_date: z.string(),
  notes: z.string().optional().default(''),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type PersonPayment = z.infer<typeof personPaymentSchema>;
