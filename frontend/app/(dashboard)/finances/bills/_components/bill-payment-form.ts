import { z } from 'zod';
import { fundedFromValues } from '@/lib/schemas/finances/category.schema';
import type { FundedFrom } from '@/lib/schemas/finances/category.schema';
import { getTodayLocalISO } from '@/lib/utils/formatters';

/** Today as a LOCAL YYYY-MM-DD string — the shared default for every payment date field. */
export const todayISO = getTodayLocalISO;

/** Shared RHF+Zod schema for both the full dialog and the row popover (S71/S75, DRY). */
export const paymentFormSchema = z.object({
  // Empty = pay the full remaining amount (design §8 "amount omitted = total").
  amount: z
    .string()
    .optional()
    .refine((v) => v === undefined || v === '' || Number(v) > 0, {
      message: 'O valor deve ser maior que zero',
    }),
  funded_from: z.enum(fundedFromValues),
  payment_date: z.string().min(1, 'Data é obrigatória'),
});

export type PaymentFormValues = z.infer<typeof paymentFormSchema>;

export const FUNDED_FROM_LABELS: Record<FundedFrom, string> = {
  caixa: 'Caixa',
  reserve: 'Reserva',
};
