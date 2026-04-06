import { z } from 'zod';

import { personSimpleSchema } from '@/lib/schemas/credit-card.schema';

export const personPaymentScheduleSchema = z.object({
  id: z.number().optional(),
  person: personSimpleSchema.optional(),
  person_id: z.number().optional(),
  reference_month: z.string(),
  due_day: z.number().min(1).max(31),
  amount: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type PersonPaymentSchedule = z.infer<typeof personPaymentScheduleSchema>;

export const bulkConfigureRequestSchema = z.object({
  person_id: z.number(),
  reference_month: z.string(),
  entries: z.array(
    z.object({
      due_day: z.number().min(1).max(31),
      amount: z
        .string()
        .or(z.number())
        .transform((val) => Number(val)),
    }),
  ),
});

export type BulkConfigureRequest = z.infer<typeof bulkConfigureRequestSchema>;

export const personMonthTotalSchema = z.object({
  total_due: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  total_offsets: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  net_total: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  total_scheduled: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  total_paid: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  pending: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
});

export type PersonMonthTotal = z.infer<typeof personMonthTotalSchema>;
