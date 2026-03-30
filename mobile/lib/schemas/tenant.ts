import { z } from "zod";

export const ApartmentSchema = z.object({
  id: z.number(),
  number: z.string(),
  building_name: z.string(),
  building_address: z.string(),
});

export const LeaseSchema = z.object({
  id: z.number(),
  start_date: z.string(),
  validity_months: z.number(),
  rental_value: z.string(),
  pending_rental_value: z.string().nullable(),
  pending_rental_value_date: z.string().nullable(),
  number_of_tenants: z.number(),
  contract_generated: z.boolean(),
});

export const DependentSchema = z.object({
  id: z.number(),
  name: z.string(),
  phone: z.string(),
  cpf_cnpj: z.string(),
});

export const TenantMeSchema = z.object({
  id: z.number(),
  name: z.string(),
  cpf_cnpj: z.string(),
  is_company: z.boolean(),
  rg: z.string(),
  phone: z.string(),
  marital_status: z.string(),
  profession: z.string(),
  due_day: z.number(),
  warning_count: z.number(),
  dependents: z.array(DependentSchema),
  lease: LeaseSchema.optional(),
  apartment: ApartmentSchema.optional(),
});

export const RentPaymentSchema = z.object({
  id: z.number(),
  reference_month: z.string(),
  amount_paid: z.string(),
  payment_date: z.string(),
  notes: z.string(),
});

export const RentAdjustmentSchema = z.object({
  id: z.number(),
  adjustment_date: z.string(),
  percentage: z.string(),
  previous_value: z.string(),
  new_value: z.string(),
  apartment_updated: z.boolean(),
});

export const PixPayloadSchema = z.object({
  pix_key: z.string(),
  pix_key_type: z.string(),
  amount: z.string(),
  merchant_name: z.string(),
  payload: z.string(),
});

export const PaymentProofSchema = z.object({
  id: z.number(),
  lease: z.number(),
  reference_month: z.string(),
  file: z.string(),
  pix_code: z.string(),
  status: z.enum(["pending", "approved", "rejected"]),
  reviewed_by: z.number().nullable(),
  reviewed_at: z.string().nullable(),
  rejection_reason: z.string(),
  created_at: z.string(),
});

export const SimulateDueDateSchema = z.object({
  current_due_day: z.number(),
  new_due_day: z.number(),
  days_difference: z.number(),
  daily_rate: z.string(),
  fee: z.string(),
});

export const TenantNotificationSchema = z.object({
  id: z.number(),
  type: z.string(),
  title: z.string(),
  body: z.string(),
  is_read: z.boolean(),
  read_at: z.string().nullable(),
  sent_at: z.string(),
  data: z.record(z.unknown()).nullable(),
});

export const PaginatedResponseSchema = <T extends z.ZodTypeAny>(itemSchema: T) =>
  z.object({
    count: z.number(),
    next: z.string().nullable(),
    previous: z.string().nullable(),
    results: z.array(itemSchema),
  });

export type TenantMe = z.infer<typeof TenantMeSchema>;
export type RentPayment = z.infer<typeof RentPaymentSchema>;
export type RentAdjustment = z.infer<typeof RentAdjustmentSchema>;
export type PixPayload = z.infer<typeof PixPayloadSchema>;
export type PaymentProof = z.infer<typeof PaymentProofSchema>;
export type SimulateDueDate = z.infer<typeof SimulateDueDateSchema>;
export type TenantNotification = z.infer<typeof TenantNotificationSchema>;
