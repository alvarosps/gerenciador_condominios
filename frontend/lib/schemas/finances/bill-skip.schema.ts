import { z } from 'zod';

export const billSkipSchema = z.object({
  id: z.number().optional(),
  billing_account: z.number().optional(),
  billing_account_id: z.number().optional(),
  reference_month: z.string(),
});

export type BillSkip = z.infer<typeof billSkipSchema>;
