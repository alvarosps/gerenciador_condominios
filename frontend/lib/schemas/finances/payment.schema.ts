import { z } from 'zod';
import { fundedFromEnum } from './category.schema';
import { condominiumRefSchema, moneyField } from './money';

export const paymentAllocationSchema = z.object({
  id: z.number().optional(),
  bill: z.number(),
  amount: moneyField,
});

export const paymentSchema = z.object({
  id: z.number().optional(),
  condominium: condominiumRefSchema.optional(),
  condominium_id: z.number().optional(),
  payment_date: z.string(),
  amount: moneyField,
  method: z.string().optional().default(''),
  funded_from: fundedFromEnum,
  reference: z.string().optional().default(''),
  notes: z.string().optional().default(''),
  allocations: z.array(paymentAllocationSchema).default([]),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type Payment = z.infer<typeof paymentSchema>;
export type PaymentAllocation = z.infer<typeof paymentAllocationSchema>;
