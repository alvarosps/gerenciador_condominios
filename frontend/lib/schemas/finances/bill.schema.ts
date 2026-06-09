import { z } from 'zod';
import { buildingSchema } from '../building.schema';
import { billingAccountSchema, billingAccountTypeEnum } from './billing-account.schema';
import {
  billBehaviorEnum,
  billLifecycleStateEnum,
  financeCategorySchema,
  paymentStatusEnum,
} from './category.schema';
import { condominiumRefSchema, moneyField } from './money';

export const billLineItemSchema = z.object({
  id: z.number().optional(),
  category: financeCategorySchema.nullable().optional(),
  description: z.string(),
  amount: moneyField, // string Decimal >= 0; the front never recalculates amount_total (§4.1)
  is_offset: z.boolean().default(false),
});

// Readings-only statements (§3.2/§3.3): NO money fields — the money lives in BillLineItem
// (single source). Mirror WaterBillStatement / ElectricityBillStatement (S58 serializer) verbatim.
export const waterStatementSchema = z.object({
  id: z.number().optional(),
  consumo_m3: z.number(),
  leitura_anterior: z.number().nullable().optional(),
  leitura_atual: z.number().nullable().optional(),
  leitura_dias: z.number().nullable().optional(),
  data_leitura: z.string().nullable().optional(),
  agua_status: z.enum(['active', 'cut']).default('active'),
  esgoto_status: z.enum(['active', 'cut']).default('active'),
});

export const electricityStatementSchema = z.object({
  id: z.number().optional(),
  consumo_kwh: z.number(),
  energia_injetada_kwh: z.number().nullable().optional(),
  leitura_anterior: z.number().nullable().optional(),
  leitura_atual: z.number().nullable().optional(),
  leitura_dias: z.number().nullable().optional(),
  classe: z.string().optional().default(''),
  bandeira: z.string().optional().default(''),
});

export const billSchema = z.object({
  id: z.number().optional(),
  condominium: condominiumRefSchema.optional(),
  condominium_id: z.number().optional(),
  building: buildingSchema.nullable().optional(),
  building_id: z.number().nullable().optional(),
  category: financeCategorySchema.nullable().optional(),
  category_id: z.number().nullable().optional(),
  competence_month: z.string(),
  due_date: z.string(),
  issue_date: z.string().nullable().optional(),
  description: z.string(),
  external_identifier: z.string().optional().default(''),
  behavior: billBehaviorEnum,
  billing_account: billingAccountSchema.nullable().optional(),
  billing_account_id: z.number().nullable().optional(),
  lifecycle_state: billLifecycleStateEnum,
  notes: z.string().optional().default(''),
  line_items: z.array(billLineItemSchema).default([]),
  water_statement: waterStatementSchema.nullable().optional(),
  electricity_statement: electricityStatementSchema.nullable().optional(),
  // Read-only annotations from Bill.objects.with_amounts(today) — never recomputed (§4.4).
  amount_total: moneyField.optional(),
  amount_paid: moneyField.optional(),
  amount_remaining: moneyField.optional(),
  payment_status: paymentStatusEnum.optional(),
  is_overdue: z.boolean().optional(),
  // Derived structural type (água/luz directly, IPTU parcela via installment→plan, else generic).
  account_type: billingAccountTypeEnum.optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type Bill = z.infer<typeof billSchema>;
export type BillLineItem = z.infer<typeof billLineItemSchema>;
export type WaterStatement = z.infer<typeof waterStatementSchema>;
export type ElectricityStatement = z.infer<typeof electricityStatementSchema>;
