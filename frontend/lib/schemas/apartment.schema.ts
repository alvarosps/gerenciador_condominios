import { z } from 'zod';
import { buildingSchema } from './building.schema';
import { furnitureSchema } from './furniture.schema';

export const apartmentSchema = z.object({
  id: z.number().optional(),
  // building_id is only used for creating/updating, not returned by API
  building_id: z.number().positive('Selecione um prédio').optional(),
  building: buildingSchema.optional(),
  number: z.number().positive('Número deve ser positivo'),
  rental_value: z.string().or(z.number()).transform((val) => Number(val)),
  rental_value_double: z
    .string()
    .or(z.number())
    .nullable()
    .optional()
    .transform((val) => (val !== null && val !== undefined ? Number(val) : null)),
  cleaning_fee: z
    .string()
    .or(z.number())
    .transform((val) => Number(val))
    .refine((val) => val >= 0, 'Valor não pode ser negativo'),
  max_tenants: z.number().positive('Deve ter pelo menos 1 inquilino'),
  is_rented: z.boolean().default(false),
  last_rent_increase_date: z.string().nullable().optional(),
  owner: z.object({ id: z.number(), name: z.string() }).nullable().optional(),
  owner_id: z.number().nullable().optional(),
  active_lease: z
    .object({
      id: z.number(),
      contract_generated: z.boolean(),
      contract_signed: z.boolean(),
      interfone_configured: z.boolean(),
      start_date: z.string(),
      validity_months: z.number(),
      rental_value: z
        .string()
        .or(z.number())
        .transform((val) => Number(val)),
      pending_rental_value: z
        .string()
        .or(z.number())
        .nullable()
        .optional()
        .transform((val) => (val !== null && val !== undefined ? Number(val) : null)),
      pending_rental_value_date: z.string().nullable().optional(),
      responsible_tenant: z.object({ id: z.number(), name: z.string() }),
    })
    .nullable()
    .optional(),
  furnitures: z.array(furnitureSchema).default([]),
  furniture_ids: z.array(z.number()).optional(),
});

export type Apartment = z.infer<typeof apartmentSchema>;
