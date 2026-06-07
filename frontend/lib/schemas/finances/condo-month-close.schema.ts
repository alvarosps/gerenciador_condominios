import { z } from 'zod';
import { moneyField } from './money';

export const MONTH_CLOSE_STATUSES = ['open', 'closed'] as const;
export type MonthCloseStatus = (typeof MONTH_CLOSE_STATUSES)[number];

const condominiumSimpleSchema = z.object({
  id: z.number(),
  name: z.string(),
});

export const condoMonthCloseSchema = z.object({
  id: z.number().optional(),
  condominium: condominiumSimpleSchema.optional(),
  reference_month: z.string(),
  status: z.enum(MONTH_CLOSE_STATUSES),
  closed_at: z.string().nullable().optional(),
  net_result: moneyField,
  cash_balance_end: moneyField,
  reserve_balance_end: moneyField,
  carry_forward_out: moneyField,
  breakdown: z.record(z.string(), z.unknown()).optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type CondoMonthClose = z.infer<typeof condoMonthCloseSchema>;

export interface CondoMonthCloseFilters {
  status?: MonthCloseStatus;
  reference_month?: string;
}
