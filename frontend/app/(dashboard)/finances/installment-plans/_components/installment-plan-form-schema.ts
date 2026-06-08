import { z } from 'zod';

/**
 * Local form schema for the installment-plan create/edit modal.
 *
 * Mirrors the writable InstallmentPlan fields. The schedule (Installments) is NOT edited
 * here — it is materialized by the service (S41) and edited in installment-schedule-field.
 * embedded=true requires linked_billing_account_id (design §7); enforced via superRefine (PT).
 */
export const installmentPlanFormSchema = z
  .object({
    description: z.string().min(1, 'Descrição é obrigatória'),
    category_id: z.number().nullable(),
    building_id: z.number().nullable(),
    total_amount: z.number().min(0, 'O valor não pode ser negativo'),
    installment_count: z.number().int().positive('Número de parcelas inválido'),
    start_due_date: z.string().min(1, 'Data da primeira parcela é obrigatória'),
    default_due_day: z.number().int().min(1).max(31),
    embedded: z.boolean(),
    linked_billing_account_id: z.number().nullable(),
    notes: z.string(),
  })
  .superRefine((data, ctx) => {
    if (data.embedded && data.linked_billing_account_id === null) {
      ctx.addIssue({
        code: 'custom',
        path: ['linked_billing_account_id'],
        message: 'Conta recorrente vinculada é obrigatória para parcela embutida',
      });
    }
  });

export type InstallmentPlanFormValues = z.infer<typeof installmentPlanFormSchema>;
