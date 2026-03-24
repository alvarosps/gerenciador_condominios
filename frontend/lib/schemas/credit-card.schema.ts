import { z } from 'zod';

export const personSimpleSchema = z.object({
  id: z.number().optional(),
  name: z.string(),
  relationship: z.string(),
  phone: z.string().optional().default(''),
  email: z.string().optional().default(''),
  is_owner: z.boolean().default(false),
  is_employee: z.boolean().default(false),
  notes: z.string().optional().default(''),
});

export type PersonSimple = z.infer<typeof personSimpleSchema>;

export const creditCardSchema = z.object({
  id: z.number().optional(),
  person: personSimpleSchema.optional(),
  person_id: z.number().optional(),
  nickname: z.string().min(1, 'Apelido é obrigatório'),
  last_four_digits: z.string().max(4).default(''),
  closing_day: z.number().min(1).max(31),
  due_day: z.number().min(1).max(31),
  is_active: z.boolean().default(true),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type CreditCard = z.infer<typeof creditCardSchema>;
