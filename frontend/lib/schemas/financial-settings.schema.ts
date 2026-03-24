import { z } from 'zod';

export const financialSettingsSchema = z.object({
  id: z.number().optional(),
  initial_balance: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  initial_balance_date: z.string(),
  notes: z.string().optional().default(''),
  updated_at: z.string().optional(),
  updated_by: z.number().nullable().optional(),
});

export type FinancialSettings = z.infer<typeof financialSettingsSchema>;
