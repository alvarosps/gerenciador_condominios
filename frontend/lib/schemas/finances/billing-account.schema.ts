import { z } from 'zod';
import { buildingSchema } from '../building.schema';
import {
  billingAccountStateEnum,
  financeCategorySchema,
} from './category.schema';
import { condominiumRefSchema, moneyFieldRounded } from './money';

export const billingAccountTypeValues = [
  'water',
  'electricity',
  'iptu',
  'internet',
  'generic',
] as const;

export const billingAccountTypeEnum = z.enum(billingAccountTypeValues);
export const supplyStatusEnum = z.enum(['active', 'cut']);

export const billingAccountSchema = z.object({
  id: z.number().optional(),
  condominium: condominiumRefSchema.optional(),
  condominium_id: z.number().optional(),
  building: buildingSchema.nullable().optional(),
  building_id: z.number().nullable().optional(),
  category: financeCategorySchema.nullable().optional(),
  category_id: z.number().nullable().optional(),
  name: z.string().min(1, 'Nome é obrigatório'),
  external_identifier: z.string().optional().default(''),
  account_type: billingAccountTypeEnum.default('generic'),
  holder_name: z.string().optional().default(''),
  registered_address: z.string().optional().default(''),
  secondary_identifier: z.string().optional().default(''),
  supply_status: supplyStatusEnum.default('active'),
  description: z.string().optional().default(''),
  default_due_day: z.number().min(1).max(31),
  expected_amount: moneyFieldRounded,
  lifecycle_state: billingAccountStateEnum,
  tracking_start_month: z.string().nullable().optional(),
  end_date: z.string().nullable().optional(),
  notes: z.string().optional().default(''),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type BillingAccount = z.infer<typeof billingAccountSchema>;
export type BillingAccountType = z.infer<typeof billingAccountTypeEnum>;
export type SupplyStatus = z.infer<typeof supplyStatusEnum>;

/** PT labels per account type — single source for every BillingAccount select/label (DRY §8.2). */
export const ACCOUNT_TYPE_LABELS: Record<BillingAccountType, string> = {
  water: 'Água',
  electricity: 'Luz',
  iptu: 'IPTU',
  internet: 'Internet',
  generic: 'Genérica',
};

/**
 * Disambiguated select label: "name — tipo · external_identifier" (falls back to
 * secondary_identifier, then to just "name — tipo"). Two same-type accounts (e.g. two Luz
 * accounts) stay distinguishable by their inscrição/UC (design §8.2-desambiguação).
 */
export function accountLabel(account: BillingAccount): string {
  const typeLabel = ACCOUNT_TYPE_LABELS[account.account_type];
  const id = account.external_identifier || account.secondary_identifier || '';
  return [account.name, typeLabel && `— ${typeLabel}`, id && `· ${id}`]
    .filter(Boolean)
    .join(' ');
}
