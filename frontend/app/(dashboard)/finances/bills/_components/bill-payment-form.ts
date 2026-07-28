import { z } from 'zod';
import { fundedFromValues } from '@/lib/schemas/finances/category.schema';
import type { FundedFrom } from '@/lib/schemas/finances/category.schema';
import { getTodayLocalISO } from '@/lib/utils/formatters';

/** Today as a LOCAL YYYY-MM-DD string — the shared default for every payment date field. */
export const todayISO = getTodayLocalISO;

/** Shared RHF+Zod schema for both the full dialog and the row popover (S71/S75, DRY). */
export const paymentFormSchema = z
  .object({
    // Empty = pay the full remaining amount (design §8 "amount omitted = total").
    amount: z
      .string()
      .optional()
      .refine((v) => v === undefined || v === '' || Number(v) > 0, {
        message: 'O valor deve ser maior que zero',
      }),
    funded_from: z.enum(fundedFromValues),
    // 0 = "nobody chosen yet"; only meaningful when funded_from is `third_party`. NOT `.default(0)`
    // — a Zod default makes the field optional on the schema's INPUT type while staying required on
    // the output, and RHF then refuses the resolver as incompatible. Both call sites always seed it.
    paid_by_person_id: z.number().int().nonnegative(),
    payment_date: z.string().min(1, 'Data é obrigatória'),
  })
  .superRefine((data, ctx) => {
    // `third_party` without a person would be a 400 from the backend. Catching it here keeps the
    // user from discovering the rule through an error toast (S82 §1).
    if (data.funded_from === 'third_party' && data.paid_by_person_id <= 0) {
      ctx.addIssue({
        code: 'custom',
        path: ['paid_by_person_id'],
        message: 'Selecione quem pagou',
      });
    }
  });

export type PaymentFormValues = z.infer<typeof paymentFormSchema>;

export const FUNDED_FROM_LABELS: Record<FundedFrom, string> = {
  caixa: 'Caixa',
  reserve: 'Reserva',
  third_party: 'Terceiro',
};

/**
 * Sources offered by the *detailed* payment dialog. `third_party` is deliberately absent: it
 * requires a person selector, which lives only in the row popover (S82 §1). Offering it here
 * would produce a payload the backend always rejects.
 */
export const DIALOG_FUNDED_FROM_VALUES: readonly FundedFrom[] = ['caixa', 'reserve'];
