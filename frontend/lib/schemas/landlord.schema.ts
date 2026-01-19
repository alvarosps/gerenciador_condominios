import { z } from 'zod';

/**
 * Zod schema for Landlord (LOCADOR) model.
 *
 * Used for validation and type inference in the Settings page
 * for landlord configuration management.
 */
export const landlordSchema = z.object({
  id: z.number().optional(),
  name: z.string().min(1, 'Nome é obrigatório'),
  nationality: z.string().default('Brasileira'),
  marital_status: z.string().min(1, 'Estado civil é obrigatório'),
  cpf_cnpj: z.string().min(1, 'CPF/CNPJ é obrigatório'),
  rg: z.string().nullable().optional(),
  phone: z.string().min(1, 'Telefone é obrigatório'),
  email: z.union([z.string().email('Email inválido'), z.literal('')]).nullable().optional(),
  street: z.string().min(1, 'Rua é obrigatória'),
  street_number: z.string().min(1, 'Número é obrigatório'),
  complement: z.string().nullable().optional(),
  neighborhood: z.string().min(1, 'Bairro é obrigatório'),
  city: z.string().min(1, 'Cidade é obrigatória'),
  state: z.string().min(1, 'Estado é obrigatório'),
  zip_code: z.string().min(1, 'CEP é obrigatório'),
  country: z.string().default('Brasil'),
  is_active: z.boolean().default(true),
  full_address: z.string().optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type Landlord = z.infer<typeof landlordSchema>;

/**
 * Zod schema for landlord form (without read-only fields).
 * Used for form validation in the Settings page.
 */
export const landlordFormSchema = z.object({
  name: z.string().min(1, 'Nome é obrigatório'),
  nationality: z.string().min(1, 'Nacionalidade é obrigatória'),
  marital_status: z.string().min(1, 'Estado civil é obrigatório'),
  cpf_cnpj: z.string().min(1, 'CPF/CNPJ é obrigatório'),
  rg: z.string().nullable().optional(),
  phone: z.string().min(1, 'Telefone é obrigatório'),
  email: z.union([z.string().email('Email inválido'), z.literal('')]).nullable().optional(),
  street: z.string().min(1, 'Rua é obrigatória'),
  street_number: z.string().min(1, 'Número é obrigatório'),
  complement: z.string().nullable().optional(),
  neighborhood: z.string().min(1, 'Bairro é obrigatório'),
  city: z.string().min(1, 'Cidade é obrigatória'),
  state: z.string().min(1, 'Estado é obrigatório'),
  zip_code: z.string().min(1, 'CEP é obrigatório'),
  country: z.string().min(1, 'País é obrigatório'),
  is_active: z.boolean(),
});

export type LandlordFormData = z.infer<typeof landlordFormSchema>;
