import { z } from 'zod';

export const buildingSchema = z.object({
  id: z.number().optional(),
  street_number: z.number().positive('Número deve ser positivo'),
  name: z.string().min(1, 'Nome é obrigatório'),
  address: z.string().min(1, 'Endereço é obrigatório'),
});

export type Building = z.infer<typeof buildingSchema>;
