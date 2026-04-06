import { z } from 'zod';

export const rentAdjustmentSchema = z.object({
  id: z.number(),
  lease: z.number(),
  lease_summary: z
    .object({
      apartment_number: z.number(),
      building_name: z.string(),
      tenant_name: z.string(),
    })
    .optional(),
  adjustment_date: z.string(),
  percentage: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  previous_value: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  new_value: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  apartment_updated: z.boolean(),
  created_at: z.string().optional(),
  created_by: z.number().nullable().optional(),
});

export type RentAdjustment = z.infer<typeof rentAdjustmentSchema>;

export const rentAdjustmentFormSchema = z.object({
  percentage: z.number().refine((v) => v !== 0, 'Percentual não pode ser zero'),
  update_apartment_prices: z.boolean().default(true),
});

export type RentAdjustmentFormValues = z.infer<typeof rentAdjustmentFormSchema>;

export const rentAdjustmentAlertSchema = z.object({
  lease_id: z.number(),
  apartment: z.string(),
  tenant: z.string(),
  rental_value: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  eligible_date: z.string(),
  days_until: z.number(),
  status: z.enum(['upcoming', 'overdue']),
  last_adjustment: z
    .object({
      id: z.number(),
      date: z.string(),
      percentage: z
        .string()
        .or(z.number())
        .transform((val) => Number(val)),
    })
    .nullable(),
  last_rent_increase_date: z.string(),
  prepaid_warning: z.boolean(),
  ipca_percentage: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  ipca_source: z.enum(['ipca', 'fallback']),
  new_value: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
});

export type RentAdjustmentAlert = z.infer<typeof rentAdjustmentAlertSchema>;
