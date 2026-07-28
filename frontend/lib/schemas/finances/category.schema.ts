import { z } from 'zod';
import { condominiumRefSchema } from './money';

export const billingAccountStateValues = ['active', 'suspended', 'deferred', 'ended'] as const;
export const billLifecycleStateValues = ['active', 'suspended', 'deferred', 'canceled'] as const;
export const billBehaviorValues = ['one_time', 'recurring', 'installment'] as const;
export const paymentStatusValues = ['open', 'partial', 'paid'] as const;
/**
 * Payment funding sources. `third_party` (S80) means a person paid with her own money: the bill is
 * settled but NOTHING leaves the caixa — the debt migrates from the utility to that person, and it
 * is only extinguished by a `ThirdPartySettlement`. It therefore ALWAYS travels with a
 * `paid_by_person_id` (the backend rejects it otherwise).
 */
export const fundedFromValues = ['caixa', 'reserve', 'third_party'] as const;

export const billingAccountStateEnum = z.enum(billingAccountStateValues);
export const billLifecycleStateEnum = z.enum(billLifecycleStateValues);
export const billBehaviorEnum = z.enum(billBehaviorValues);
export const paymentStatusEnum = z.enum(paymentStatusValues);
export const fundedFromEnum = z.enum(fundedFromValues);

/** Parent as serialized by CategorySimpleSerializer ({ id, name }) — not recursive (S38). */
const categoryParentSchema = z.object({ id: z.number(), name: z.string() });

export const financeCategorySchema = z.object({
  id: z.number().optional(),
  condominium: condominiumRefSchema.optional(),
  condominium_id: z.number().optional(),
  parent: categoryParentSchema.nullable().optional(),
  parent_id: z.number().nullable().optional(),
  name: z.string().min(1, 'Nome é obrigatório'),
  color: z.string().optional().default(''),
  sort_order: z.number().optional().default(0),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type FinanceCategory = z.infer<typeof financeCategorySchema>;
export type BillingAccountState = z.infer<typeof billingAccountStateEnum>;
export type BillLifecycleState = z.infer<typeof billLifecycleStateEnum>;
export type BillBehavior = z.infer<typeof billBehaviorEnum>;
export type PaymentStatus = z.infer<typeof paymentStatusEnum>;
export type FundedFrom = z.infer<typeof fundedFromEnum>;
