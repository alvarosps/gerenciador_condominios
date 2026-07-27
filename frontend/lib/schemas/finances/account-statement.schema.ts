import { z } from 'zod';
import { billingAccountSchema } from './billing-account.schema';
import { moneyField } from './money';

// Payload of GET billing-accounts/{id}/statement (S67) — a PLAIN object (not {results,count}).
export const statementMonthRowSchema = z.object({
  bill_id: z.number(),
  competence_month: z.string(),
  due_date: z.string(),
  description: z.string(),
  amount_total: moneyField,
  amount_paid: moneyField,
  amount_remaining: moneyField,
  payment_status: z.string(),
  lifecycle_state: z.string(),
  amount_is_estimated: z.boolean(),
  paid_date: z.string().nullable(), // MAX(payment_date) of the live allocations; null if unpaid
});

export const statementPlanRowSchema = z.object({
  id: z.number(),
  description: z.string(),
  installment_count: z.number().int(),
  materialized_count: z.number().int(),
  lifecycle_state: z.string(),
  embedded: z.boolean(),
});

export const accountStatementSchema = z.object({
  account: billingAccountSchema, // already carries open_balance (optional)
  stats: z.object({
    open_balance: z.string(), // decimal string (contract S67)
    open_bills_count: z.number().int(),
    avg_delay_days: z.number().int().nullable(), // null = no eligible paid-off bill
  }),
  months: z.array(statementMonthRowSchema),
  plans: z.array(statementPlanRowSchema),
});

export type AccountStatement = z.infer<typeof accountStatementSchema>;
export type StatementMonthRow = z.infer<typeof statementMonthRowSchema>;
export type StatementPlanRow = z.infer<typeof statementPlanRowSchema>;
