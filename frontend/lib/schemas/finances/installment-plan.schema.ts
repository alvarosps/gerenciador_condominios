import { z } from 'zod';
import { buildingSchema } from '../building.schema';
import { billingAccountSchema } from './billing-account.schema';
import { financeCategorySchema } from './category.schema';
import { condominiumRefSchema, moneyFieldRounded } from './money';

export const installmentPlanStateValues = ['active', 'paid', 'deferred', 'canceled'] as const;
export const installmentPlanStateEnum = z.enum(installmentPlanStateValues);
export type InstallmentPlanState = z.infer<typeof installmentPlanStateEnum>;

export const installmentSchema = z.object({
  id: z.number().optional(),
  plan: z.number().optional(), // PK of the parent plan (read-only on the backend)
  number: z.number().optional(), // read-only (fixed at materialization)
  due_date: z.string(), // YYYY-MM-DD (schedule, editable via PATCH)
  amount: moneyFieldRounded, // string Decimal >= 0 (schedule, editable); never recomputed in the FE
  is_overdue: z.boolean().optional(), // read-only annotation (S42)
});

export type Installment = z.infer<typeof installmentSchema>;

export const installmentPlanSchema = z
  .object({
    id: z.number().optional(),
    condominium: condominiumRefSchema.optional(),
    condominium_id: z.number().optional(),
    description: z.string().min(1, 'Descrição é obrigatória'),
    total_amount: moneyFieldRounded, // string Decimal; the FE never recalculates amount_total (§4.4)
    installment_count: z.number().int().positive('Número de parcelas inválido'),
    start_due_date: z.string(), // YYYY-MM-DD
    default_due_day: z.number().int().min(1).max(31),
    lifecycle_state: installmentPlanStateEnum,
    embedded: z.boolean().default(false),
    category: financeCategorySchema.nullable().optional(), // nested read (S39)
    category_id: z.number().nullable().optional(), // write
    building: buildingSchema.nullable().optional(),
    building_id: z.number().nullable().optional(), // null = condominium level
    billing_account: billingAccountSchema.nullable().optional(),
    billing_account_id: z.number().nullable().optional(), // owner of any plan (consumption/IPTU/null)
    installments: z.array(installmentSchema).default([]), // nested read-only
    notes: z.string().optional().default(''),
    created_at: z.string().optional(),
    updated_at: z.string().optional(),
  })
  .superRefine((data, ctx) => {
    // An embedded plan must be linked to a recurring account. On WRITE the form supplies
    // `billing_account_id`; on READ the API returns the nested `billing_account` object only
    // (`billing_account_id` is write_only on the serializer). Require that at least one is
    // present — checking only the id would wrongly reject every embedded plan parsed from a
    // read response, throwing inside .map(parse) and emptying the whole list.
    const hasLinkedAccount =
      (data.billing_account_id !== null && data.billing_account_id !== undefined) ||
      (data.billing_account !== null && data.billing_account !== undefined);
    if (data.embedded && !hasLinkedAccount) {
      ctx.addIssue({
        code: 'custom',
        path: ['billing_account_id'],
        message: 'Conta recorrente vinculada é obrigatória para parcela embutida',
      });
    }
  });

export type InstallmentPlan = z.infer<typeof installmentPlanSchema>;
