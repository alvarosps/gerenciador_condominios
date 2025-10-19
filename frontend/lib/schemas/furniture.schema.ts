import { z } from 'zod';

export const furnitureSchema = z.object({
  id: z.number().optional(),
  name: z.string().min(1, 'Nome é obrigatório'),
});

export type Furniture = z.infer<typeof furnitureSchema>;
