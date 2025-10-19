import { z } from 'zod';
import { apartmentSchema } from './apartment.schema';
import { tenantSchema } from './tenant.schema';

export const leaseSchema = z.object({
  id: z.number().optional(),
  apartment_id: z.number().positive('Selecione um apartamento'),
  apartment: apartmentSchema.optional(),
  responsible_tenant_id: z.number().positive('Selecione o inquilino responsável'),
  responsible_tenant: tenantSchema.optional(),
  tenants: z.array(tenantSchema).default([]),
  tenant_ids: z.array(z.number()).optional(),
  start_date: z.string().min(1, 'Data de início é obrigatória'),
  final_date: z.string().optional().nullable(),
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
  number_of_tenants: z.number().optional(),
  pdf_path: z.string().optional().nullable(),
});

export type Lease = z.infer<typeof leaseSchema>;
