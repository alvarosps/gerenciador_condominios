import { z } from 'zod';
import { creditCardSchema } from './credit-card.schema';

export const personSchema = z.object({
  id: z.number().optional(),
  name: z.string().min(1, 'Nome é obrigatório'),
  relationship: z.string().min(1, 'Relação é obrigatória'),
  phone: z.string().optional().default(''),
  email: z.string().optional().default(''),
  is_owner: z.boolean().default(false),
  is_employee: z.boolean().default(false),
  user: z.number().nullable().optional(),
  user_id: z.number().nullable().optional(),
  notes: z.string().optional().default(''),
  credit_cards: z.array(creditCardSchema).default([]),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type Person = z.infer<typeof personSchema>;
