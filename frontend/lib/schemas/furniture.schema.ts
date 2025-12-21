import { z } from 'zod';

export const furnitureSchema = z.object({
  id: z.number().optional(),
  name: z.string().min(1, 'Nome é obrigatório'),
  description: z.string().optional().nullable(),
  created_at: z.string().optional(),
});

export type Furniture = z.infer<typeof furnitureSchema>;
