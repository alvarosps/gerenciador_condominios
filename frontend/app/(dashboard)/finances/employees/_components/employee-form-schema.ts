import { z } from 'zod';
import { employeePaymentTypeValues } from '@/lib/schemas/finances/employee.schema';

/**
 * Local form schema for the employee create/edit modal.
 *
 * fixed/mixed require a positive base salary; variable must NOT have one (backend clean(), §18).
 * The salary-offset (Rosa, §4.6) is computed entirely on the backend — the form only links
 * person_id/lease_id.
 */
export const employeeFormSchema = z
  .object({
    name: z.string().min(1, 'Nome é obrigatório'),
    role: z.string(),
    payment_type: z.enum(employeePaymentTypeValues),
    base_salary: z.number().min(0, 'O salário não pode ser negativo').nullable(),
    default_due_day: z.number().int().min(1).max(31),
    is_active: z.boolean(),
    person_id: z.number().nullable(),
    lease_id: z.number().nullable(),
    notes: z.string(),
  })
  .superRefine((data, ctx) => {
    const needsBase = data.payment_type === 'fixed' || data.payment_type === 'mixed';
    if (needsBase && (data.base_salary === null || data.base_salary <= 0)) {
      ctx.addIssue({
        code: 'custom',
        path: ['base_salary'],
        message: 'Salário base é obrigatório para funcionário fixo ou misto',
      });
    }
  });

export type EmployeeFormValues = z.infer<typeof employeeFormSchema>;
