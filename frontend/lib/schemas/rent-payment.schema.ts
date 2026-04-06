import { z } from 'zod';
import { leaseSchema } from './lease.schema';

export const rentPaymentSchema = z.object({
  id: z.number().optional(),
  lease: leaseSchema.optional(),
  lease_id: z.number().optional(),
  reference_month: z.string(),
  amount_paid: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  payment_date: z.string(),
  notes: z.string().optional().default(''),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type RentPayment = z.infer<typeof rentPaymentSchema>;
