import { z } from 'zod';
import { buildingSchema } from './building.schema';
import { furnitureSchema } from './furniture.schema';

export const apartmentSchema = z.object({
  id: z.number().optional(),
  building_id: z.number().positive('Selecione um prédio'),
  building: buildingSchema.optional(),
  number: z.number().positive('Número deve ser positivo'),
  interfone_configured: z.boolean().default(false),
  contract_generated: z.boolean().default(false),
  contract_signed: z.boolean().default(false),
  rental_value: z.string().or(z.number()).transform((val) => Number(val)),
  cleaning_fee: z
    .string()
    .or(z.number())
    .transform((val) => Number(val))
    .refine((val) => val >= 0, 'Valor não pode ser negativo'),
  max_tenants: z.number().positive('Deve ter pelo menos 1 inquilino'),
  is_rented: z.boolean().default(false),
  lease_date: z.string().nullable().optional(),
  last_rent_increase_date: z.string().nullable().optional(),
  furnitures: z.array(furnitureSchema).default([]),
  furniture_ids: z.array(z.number()).optional(),
});

export type Apartment = z.infer<typeof apartmentSchema>;
