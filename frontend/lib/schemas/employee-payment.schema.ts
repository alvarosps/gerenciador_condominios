import { z } from 'zod';
import { personSimpleSchema } from './credit-card.schema';

export const employeePaymentSchema = z.object({
  id: z.number().optional(),
  person: personSimpleSchema.optional(),
  person_id: z.number().optional(),
  reference_month: z.string(),
  base_salary: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  variable_amount: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  rent_offset: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  cleaning_count: z.number().default(0),
  payment_date: z.string().nullable().optional(),
  is_paid: z.boolean().default(false),
  notes: z.string().optional().default(''),
  total_paid: z
    .string()
    .or(z.number())
    .optional()
    .transform((val) => (val !== null && val !== undefined ? Number(val) : undefined)),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type EmployeePayment = z.infer<typeof employeePaymentSchema>;
