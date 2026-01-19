import { z } from 'zod';

export const buildingSchema = z.object({
  id: z.number().optional(),
  street_number: z.number().positive('Número deve ser positivo'),
  name: z.string().min(1, 'Nome é obrigatório'),
  address: z.string().min(1, 'Endereço é obrigatório'),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
  is_deleted: z.boolean().optional(),
  deleted_at: z.string().nullable().optional(),
  created_by: z.number().nullable().optional(),
  updated_by: z.number().nullable().optional(),
  deleted_by: z.number().nullable().optional(),
});

export type Building = z.infer<typeof buildingSchema>;
