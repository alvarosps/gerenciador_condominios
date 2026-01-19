import { z } from 'zod';
import { apartmentSchema } from './apartment.schema';
import { tenantSchema } from './tenant.schema';

export const leaseSchema = z.object({
  id: z.number().optional(),
  // These IDs are only used for creating/updating, not returned by API
  apartment_id: z.number().positive('Selecione um apartamento').optional(),
  apartment: apartmentSchema.optional(),
  responsible_tenant_id: z.number().positive('Selecione o inquilino responsável').optional(),
  responsible_tenant: tenantSchema.optional(),
  tenants: z.array(tenantSchema).default([]),
  tenant_ids: z.array(z.number()).optional(),
  start_date: z.string().min(1, 'Data de início é obrigatória'),
  final_date: z.string().optional().nullable(),
  next_month_date: z.string().optional().nullable(),
  validity_months: z.number().positive('Validade deve ser positiva'),
  due_day: z.number().min(1).max(31, 'Dia de vencimento deve ser entre 1 e 31'),
  rental_value: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  cleaning_fee: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  tag_fee: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  contract_generated: z.boolean().optional(),
  contract_signed: z.boolean().optional(),
  interfone_configured: z.boolean().optional(),
  warning_count: z.number().optional(),
  number_of_tenants: z.number().optional(),
  pdf_path: z.string().optional().nullable(),
  status: z.string().optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
  is_deleted: z.boolean().optional(),
  deleted_at: z.string().nullable().optional(),
  created_by: z.number().nullable().optional(),
  updated_by: z.number().nullable().optional(),
  deleted_by: z.number().nullable().optional(),
});

export type Lease = z.infer<typeof leaseSchema>;
