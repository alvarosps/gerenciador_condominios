import { z } from 'zod';

export const furnitureSchema = z.object({
  id: z.number().optional(),
  name: z.string().min(1, 'Nome é obrigatório'),
  description: z.string().optional().nullable(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
  is_deleted: z.boolean().optional(),
  deleted_at: z.string().nullable().optional(),
  created_by: z.number().nullable().optional(),
  updated_by: z.number().nullable().optional(),
  deleted_by: z.number().nullable().optional(),
});

export type Furniture = z.infer<typeof furnitureSchema>;
