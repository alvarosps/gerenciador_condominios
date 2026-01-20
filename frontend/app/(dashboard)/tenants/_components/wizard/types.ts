import { z } from 'zod';
import { UseFormReturn } from 'react-hook-form';
import {
  validateCpfCnpj,
  validateBrazilianPhone,
  validateEmail,
} from '@/lib/utils/validators';

export const MARITAL_STATUS_OPTIONS = [
  'Solteiro(a)',
  'Casado(a)',
  'Divorciado(a)',
  'Viúvo(a)',
  'União Estável',
];

export const tenantFormSchema = z.object({
  // Step 1: Basic Info
  name: z.string().min(3, 'Nome deve ter no mínimo 3 caracteres'),
  cpf_cnpj: z.string().refine((val) => validateCpfCnpj(val), {
    message: 'CPF/CNPJ inválido',
  }),
  is_company: z.boolean(),

  // Step 2: Contact Info
  phone: z.string().refine((val) => validateBrazilianPhone(val), {
    message: 'Telefone inválido',
  }),
  email: z
    .string()
    .optional()
    .refine((val) => !val || validateEmail(val), {
      message: 'Email inválido',
    }),
  phone_alternate: z
    .string()
    .optional()
    .refine((val) => !val || validateBrazilianPhone(val), {
      message: 'Telefone inválido',
    }),

  // Step 3: Professional Info
  profession: z.string().min(3, 'Profissão deve ter no mínimo 3 caracteres'),
  marital_status: z.string().min(1, 'Selecione o estado civil'),

  // Step 4: Dependents
  dependents: z
    .array(
      z.object({
        id: z.number().optional(),
        name: z.string(),
        phone: z.string(),
      })
    )
    .optional(),

  // Step 5: Furniture
  furniture_ids: z.array(z.number()).optional(),

  // Additional fields
  deposit_amount: z.number().nullable().optional(),
  cleaning_fee_paid: z.boolean().optional(),
  tag_deposit_paid: z.boolean().optional(),
  rent_due_day: z.number().optional(),
});

export type TenantFormValues = z.infer<typeof tenantFormSchema>;

export interface StepProps {
  formMethods: UseFormReturn<TenantFormValues>;
}

export const WIZARD_STEPS = [
  {
    title: 'Dados Básicos',
    description: 'Nome e documento',
    fields: ['name', 'cpf_cnpj', 'is_company'] as const,
  },
  {
    title: 'Contato',
    description: 'Telefone e email',
    fields: ['phone', 'email', 'phone_alternate'] as const,
  },
  {
    title: 'Profissão',
    description: 'Informações profissionais',
    fields: ['profession', 'marital_status'] as const,
  },
  {
    title: 'Dependentes',
    description: 'Dependentes do inquilino',
    fields: [] as const,
  },
  {
    title: 'Móveis',
    description: 'Móveis do inquilino',
    fields: [] as const,
  },
  {
    title: 'Revisão',
    description: 'Conferir dados',
    fields: [] as const,
  },
];
