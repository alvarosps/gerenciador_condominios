import { z } from 'zod';
import { buildingSchema } from '../building.schema';
import {
  billingAccountStateEnum,
  financeCategorySchema,
} from './category.schema';
import { condominiumRefSchema, moneyFieldRounded } from './money';

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
