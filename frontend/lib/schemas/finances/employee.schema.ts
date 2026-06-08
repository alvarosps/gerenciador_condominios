import { z } from 'zod';
import { leaseSchema } from '../lease.schema';
import { personSimpleSchema } from '../credit-card.schema';
import { condominiumRefSchema } from './money';

export const employeePaymentTypeValues = ['fixed', 'variable', 'mixed'] as const;
export const employeePaymentTypeEnum = z.enum(employeePaymentTypeValues);
export type EmployeePaymentType = z.infer<typeof employeePaymentTypeEnum>;

export const employeeSchema = z
  .object({
    id: z.number().optional(),
    condominium: condominiumRefSchema.optional(),
    condominium_id: z.number().optional(),
    name: z.string().min(1, 'Nome é obrigatório'),
    role: z.string().optional().default(''),
    payment_type: employeePaymentTypeEnum,
    base_salary: z
      .union([z.string(), z.number()])
      .nullable()
      .optional()
      .transform((val) =>
        val !== null && val !== undefined && val !== ''
          ? Math.round(Number(val) * 100) / 100
          : null,
      ), // null/0 for variable-only (Raymel, §18)
    default_due_day: z.number().int().min(1).max(31),
    is_active: z.boolean().default(true),
    notes: z.string().optional().default(''),
    person: personSimpleSchema.nullable().optional(), // nested read (PersonSimpleSerializer)
    person_id: z.number().nullable().optional(),
    lease: leaseSchema.nullable().optional(), // nested read (LeaseSerializer)
    lease_id: z.number().nullable().optional(), // salary-offset link (Rosa, §4.6)
    created_at: z.string().optional(),
    updated_at: z.string().optional(),
  })
  .superRefine((data, ctx) => {
    // fixed/mixed require a base salary; variable must NOT have one (backend clean(), §18).
    const needsBase = data.payment_type === 'fixed' || data.payment_type === 'mixed';
    if (needsBase && (data.base_salary === null || data.base_salary === undefined)) {
      ctx.addIssue({
        code: 'custom',
        path: ['base_salary'],
        message: 'Salário base é obrigatório para funcionário fixo ou misto',
      });
    }
  });

export type Employee = z.infer<typeof employeeSchema>;
