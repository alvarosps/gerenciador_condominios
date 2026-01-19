import { z } from 'zod';
import { furnitureSchema } from './furniture.schema';

export const dependentSchema = z.object({
  id: z.number().optional(),
  name: z.string().min(1, 'Nome é obrigatório'),
  phone: z.string().min(1, 'Telefone é obrigatório'),
  relationship: z.string().optional().nullable(),
  tenant_id: z.number().optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
  is_deleted: z.boolean().optional(),
  deleted_at: z.string().nullable().optional(),
  created_by: z.number().nullable().optional(),
  updated_by: z.number().nullable().optional(),
  deleted_by: z.number().nullable().optional(),
});

export const tenantSchema = z.object({
  id: z.number().optional(),
  name: z.string().min(1, 'Nome é obrigatório'),
  cpf_cnpj: z.string().min(1, 'CPF/CNPJ é obrigatório'),
  rg: z.string().optional().nullable(),
  phone: z.string().min(1, 'Telefone é obrigatório'),
  email: z.string().email('Email inválido').optional().nullable().or(z.literal('')),
  phone_alternate: z.string().optional().nullable(),
  marital_status: z.string().optional().nullable(),
  profession: z.string().optional().nullable(),
  is_company: z.boolean().default(false),
  deposit_amount: z
    .string()
    .or(z.number())
    .optional()
    .nullable()
    .transform((val) => (val ? Number(val) : null)),
  cleaning_fee_paid: z.boolean().optional(),
  tag_deposit_paid: z.boolean().optional(),
  rent_due_day: z.number().optional().nullable(),
  furnitures: z.array(furnitureSchema).default([]),
  furniture_ids: z.array(z.number()).optional(),
  dependents: z.array(dependentSchema).default([]),
  user_id: z.number().nullable().optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
  is_deleted: z.boolean().optional(),
  deleted_at: z.string().nullable().optional(),
  created_by: z.number().nullable().optional(),
  updated_by: z.number().nullable().optional(),
  deleted_by: z.number().nullable().optional(),
});

export type Dependent = z.infer<typeof dependentSchema>;
export type Tenant = z.infer<typeof tenantSchema>;
