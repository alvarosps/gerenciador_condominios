import { z } from 'zod';

// The /rent-payments/ endpoint returns a SLIM lease (RentPaymentSlimSerializer) — just the
// fields the admin rent-payments screen reads — to avoid the per-row N+1 the full lease caused.
// Keep these shapes minimal and in sync with core.serializers.RentPaymentLeaseSerializer.
const rentPaymentBuildingSchema = z.object({
  id: z.number(),
  name: z.string(),
});

const rentPaymentApartmentSchema = z.object({
  id: z.number(),
  number: z.number(),
  building: rentPaymentBuildingSchema.nullable().optional(),
});

const rentPaymentLeaseTenantSchema = z.object({
  id: z.number(),
  name: z.string(),
});

const rentPaymentLeaseSchema = z.object({
  id: z.number(),
  apartment: rentPaymentApartmentSchema.nullable().optional(),
  responsible_tenant: rentPaymentLeaseTenantSchema.nullable().optional(),
});

export const rentPaymentSchema = z.object({
  id: z.number().optional(),
  lease: rentPaymentLeaseSchema.optional(),
  lease_id: z.number().optional(),
  reference_month: z.string(),
  amount_paid: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  payment_date: z.string(),
  notes: z.string().optional().default(''),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type RentPayment = z.infer<typeof rentPaymentSchema>;
